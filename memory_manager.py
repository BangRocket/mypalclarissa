from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session as OrmSession

from db import SessionLocal
from models import Session, Message
from mem0_config import MEM0

SESSION_IDLE_MINUTES = 30
CARRYOVER_MESSAGE_COUNT = 10
BUFFER_MESSAGE_COUNT = 20


class MemoryManager:
    def __init__(self, llm_callable):
        """
        llm_callable: function(messages: List[Dict]) -> str
        """
        self.llm = llm_callable

    # ---------- public entrypoint ----------

    def handle_message(self, user_id: str, project_id: str, user_message: str) -> str:
        db = SessionLocal()
        try:
            sess = self._get_or_create_session(db, user_id, project_id)
            recent_msgs = self._get_recent_messages(db, sess.id)

            # 1) pull mem0 memories relevant to this query
            user_mems, proj_mems = self._fetch_mem0_context(
                user_id, project_id, user_message
            )

            # 2) build messages for the LLM
            prompt_messages = self._build_prompt(
                user_mems,
                proj_mems,
                sess.context_snapshot,
                sess.session_summary,
                recent_msgs,
                user_message,
            )

            # 3) call LLM
            assistant_reply = self.llm(prompt_messages)

            # 4) store messages in *our* DB
            self._store_message(db, sess.id, user_id, "user", user_message)
            self._store_message(db, sess.id, user_id,
                                "assistant", assistant_reply)
            sess.last_activity_at = datetime.utcnow()
            db.commit()

            # 5) send a slice of the convo to mem0 so it can extract/update memory
            self._add_to_mem0(
                user_id, project_id, recent_msgs, user_message, assistant_reply
            )

            return assistant_reply
        finally:
            db.close()

    # ---------- sessions ----------

    def _get_or_create_session(
        self, db: OrmSession, user_id: str, project_id: str
    ) -> Session:
        last = (
            db.query(Session)
            .filter_by(user_id=user_id, project_id=project_id)
            .order_by(Session.started_at.desc())
            .first()
        )
        now = datetime.utcnow()
        if not last:
            return self._create_session(db, user_id, project_id, None)

        if now - last.last_activity_at > timedelta(minutes=SESSION_IDLE_MINUTES):
            return self._create_session(db, user_id, project_id, last.id)

        return last

    def _create_session(
        self,
        db: OrmSession,
        user_id: str,
        project_id: str,
        previous_session_id: Optional[str],
    ) -> Session:
        snapshot = None
        previous_summary = None

        if previous_session_id:
            # Get previous session
            prev_session = db.query(Session).filter_by(id=previous_session_id).first()

            # Get messages for carryover
            carry = (
                db.query(Message)
                .filter_by(session_id=previous_session_id)
                .order_by(Message.created_at.desc())
                .limit(CARRYOVER_MESSAGE_COUNT)
                .all()
            )
            carry = list(reversed(carry))
            snapshot = "\n".join(
                f"{m.role.upper()}: {m.content}" for m in carry)

            # Generate summary of the previous session
            all_msgs = (
                db.query(Message)
                .filter_by(session_id=previous_session_id)
                .order_by(Message.created_at.asc())
                .all()
            )
            if all_msgs:
                previous_summary = self._summarize_session(all_msgs)
                # Store summary in the previous session
                if prev_session:
                    prev_session.session_summary = previous_summary
                    db.commit()

        new = Session(
            user_id=user_id,
            project_id=project_id,
            previous_session_id=previous_session_id,
            context_snapshot=snapshot,
            session_summary=previous_summary,  # Store previous session's summary
        )
        db.add(new)
        db.commit()
        db.refresh(new)
        return new

    def _summarize_session(self, messages: List[Message]) -> str:
        """Generate a concise summary of the session using the LLM."""
        conversation = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in messages
        )

        summary_prompt = [
            {
                "role": "system",
                "content": "Summarize this conversation in 2-3 sentences. Focus on key topics discussed, decisions made, and any important context for future conversations.",
            },
            {
                "role": "user",
                "content": conversation,
            },
        ]

        return self.llm(summary_prompt)

    def _get_recent_messages(self, db: OrmSession, session_id: str) -> List[Message]:
        msgs = (
            db.query(Message)
            .filter_by(session_id=session_id)
            .order_by(Message.created_at.desc())
            .limit(BUFFER_MESSAGE_COUNT)
            .all()
        )
        return list(reversed(msgs))

    def _store_message(
        self,
        db: OrmSession,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> None:
        msg = Message(session_id=session_id, user_id=user_id,
                      role=role, content=content)
        db.add(msg)
        db.commit()

    # ---------- mem0 integration ----------

    def _fetch_mem0_context(
        self, user_id: str, project_id: str, user_message: str
    ) -> Tuple[List[str], List[str]]:
        """
        Use mem0 search() to retrieve:
          - user-level memories (filters by user_id)
          - project-level memories (filters by user_id + project_id)
        """
        user_res = MEM0.search(
            user_message,
            user_id=user_id,
        )

        proj_res = MEM0.search(
            user_message,
            user_id=user_id,
            filters={"project_id": project_id},
        )

        user_mems = [r["memory"] for r in user_res.get("results", [])]
        proj_mems = [r["memory"] for r in proj_res.get("results", [])]

        return user_mems, proj_mems

    def _add_to_mem0(
        self,
        user_id: str,
        project_id: str,
        recent_msgs: List[Message],
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """
        Send a small slice of the recent conversation to mem0.add().
        """
        history_slice = [
            {"role": m.role, "content": m.content}
            for m in recent_msgs[-4:]
        ] + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_reply},
        ]

        MEM0.add(
            history_slice,
            user_id=user_id,
            metadata={"project_id": project_id},
        )

    # ---------- prompt building ----------

    def _build_prompt(
        self,
        user_mems: List[str],
        proj_mems: List[str],
        snapshot: Optional[str],
        session_summary: Optional[str],
        recent_msgs: List[Message],
        user_message: str,
    ) -> List[Dict[str, str]]:
        system_base = """
You are Mara, an AI assistant.

Use:
- USER MEMORY for stable facts and preferences about the user.
- PROJECT MEMORY for context about this project.
- PREVIOUS SESSION SUMMARY for a brief overview of what was discussed before.
- SESSION CONTEXT for recent messages from the previous session.
If newer information contradicts older, prefer the newest.
        """.strip()

        user_block = "\n".join(f"- {m}" for m in user_mems) or "(none)"
        proj_block = "\n".join(f"- {m}" for m in proj_mems) or "(none)"
        summary_block = session_summary or "(none)"
        session_block = snapshot or "(none)"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_base},
            {"role": "system", "content": f"USER MEMORY:\n{user_block}"},
            {"role": "system", "content": f"PROJECT MEMORY:\n{proj_block}"},
            {"role": "system", "content": f"PREVIOUS SESSION SUMMARY:\n{summary_block}"},
            {"role": "system", "content": f"SESSION CONTEXT:\n{session_block}"},
        ]

        for m in recent_msgs:
            messages.append({"role": m.role, "content": m.content})

        messages.append({"role": "user", "content": user_message})
        return messages
