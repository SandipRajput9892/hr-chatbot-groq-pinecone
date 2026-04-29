from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.groq_client import generate_response
from app.models.db_models import ChatHistory, Employee
from app.services.retrieval_service import check_source_indexed, format_context, retrieve_relevant_context
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are an intelligent HR Assistant. You help employees with:
- Company HR policies and procedures
- Leave management and entitlements
- Employee benefits and compensation
- Onboarding and offboarding
- Performance review processes
- Workplace guidelines and code of conduct

Use the provided HR document context to answer questions accurately. If information is not available in the context, say so clearly rather than guessing. Be professional, concise, and empathetic.

When asked about individual leave balances or personal data, advise employees to check their HR portal or contact HR directly, as you only have access to general policy documents."""


def _build_history(db: Session, employee_id, limit: int = 5) -> List[dict]:
    records = (
        db.query(ChatHistory)
        .filter(ChatHistory.employee_id == employee_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    messages = []
    for r in reversed(records):
        messages.append({"role": "user", "content": r.message})
        messages.append({"role": "assistant", "content": r.response})
    return messages


def chat_with_hr(
    db: Session,
    employee: Employee,
    user_message: str,
    source_filter: Optional[str] = None,
) -> Dict:
    context_matches = retrieve_relevant_context(user_message, top_k=5, source_filter=source_filter)

    if source_filter and not context_matches:
        # Empty matches could mean (a) not indexed or (b) indexed but low relevance.
        # Ask Pinecone directly rather than showing a false "not indexed" warning.
        if not check_source_indexed(source_filter):
            msg = (
                f"**{source_filter}** has not been indexed yet. "
                "Please re-upload the document so it can be searched."
            )
            db.add(ChatHistory(employee_id=employee.id, message=user_message, response=msg, sources=[]))
            db.commit()
            return {"message": msg, "sources": []}

    context = format_context(context_matches)
    messages: List[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if context:
        messages.append({
            "role": "system",
            "content": f"Relevant HR documentation:\n\n{context}",
        })

    messages.extend(_build_history(db, employee.id))
    messages.append({"role": "user", "content": user_message})

    response_text = generate_response(messages, temperature=0.3, max_tokens=1024)

    db.add(
        ChatHistory(
            employee_id=employee.id,
            message=user_message,
            response=response_text,
            sources=[m["source"] for m in context_matches],
        )
    )
    db.commit()

    unique_sources = list({m["source"] for m in context_matches})
    return {"message": response_text, "sources": unique_sources}
