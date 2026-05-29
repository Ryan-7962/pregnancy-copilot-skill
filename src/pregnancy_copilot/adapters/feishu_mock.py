from pregnancy_copilot.models import MessageEvent
from .base import MessageAdapter


class MockFeishuAdapter(MessageAdapter):
    def __init__(self) -> None:
        self.sent_replies: list[tuple[str, str]] = []
        self.docs: dict[str, dict[str, str]] = {}

    def receive_message(self, payload: dict) -> MessageEvent:
        return MessageEvent(
            message_id=payload.get("message_id", "mock-message"),
            timestamp=payload.get("timestamp", ""),
            sender_id=payload.get("sender_id", "mock-user"),
            sender_role=payload.get("sender_role", "pregnant_user"),
            chat_type=payload.get("chat_type", "p2p"),
            text=payload.get("text") or payload.get("content", ""),
            source="feishu",
            chat_id=payload.get("chat_id"),
            event_id=payload.get("event_id"),
            message_type=payload.get("message_type"),
        )

    def send_reply(self, message: MessageEvent, text: str) -> None:
        self.sent_replies.append((message.message_id, text))

    def write_doc(self, title: str, content: str) -> str:
        doc_id = f"mock-doc-{len(self.docs) + 1:03d}"
        self.docs[doc_id] = {"title": title, "content": content}
        return doc_id


FeishuMockAdapter = MockFeishuAdapter
