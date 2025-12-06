from __future__ import annotations

import os

import gradio as gr
from dotenv import load_dotenv

from db import init_db, SessionLocal
from models import Project
from memory_manager import MemoryManager
from llm_backends import make_llm

# Load .env
load_dotenv()

USER_ID = os.getenv("USER_ID", "demo-user")
DEFAULT_PROJECT = os.getenv("DEFAULT_PROJECT", "Default Project")


def init() -> MemoryManager:
    init_db()
    llm = make_llm()
    mm = MemoryManager(llm_callable=llm)
    return mm


mm = init()


def ensure_project(name: str) -> str:
    db = SessionLocal()
    try:
        proj = (
            db.query(Project)
            .filter_by(owner_id=USER_ID, name=name)
            .first()
        )
        if not proj:
            proj = Project(owner_id=USER_ID, name=name)
            db.add(proj)
            db.commit()
            db.refresh(proj)
        return proj.id
    finally:
        db.close()


def chat_fn(message: str, history, project_name: str):
    project_id = ensure_project(project_name or DEFAULT_PROJECT)
    reply = mm.handle_message(USER_ID, project_id, message)
    return reply


def main():
    with gr.Blocks() as demo:
        gr.Markdown(
            "# Clara / Mara Assistant\nSession-based chat with mem0 memory.")

        project_name = gr.Textbox(
            label="Project",
            value=DEFAULT_PROJECT,
            info="Use a different name per topic to segment memory.",
        )

        gr.ChatInterface(
            fn=lambda msg, hist: chat_fn(msg, hist, project_name.value),
            title="Clara",
            textbox=gr.Textbox(placeholder="Type your message here..."),
            type="messages",
        )

    demo.launch()


if __name__ == "__main__":
    main()
