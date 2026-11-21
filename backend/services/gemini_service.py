"""Gemini API integration service — compatible with google-genai 2.x+."""
import logging
import time

logger = logging.getLogger(__name__)

DEFAULT_ACTIVE_MODEL = 'gemini-3.5-flash'
FALLBACK_MODELS = ['gemini-3.5-flash', 'gemini-3.5-flash-lite']
RETRYABLE_ERRORS = ('ResourceExhausted', 'ServiceUnavailable', 'InternalServerError', 'DeadlineExceeded', '429', '503', '500')


def _normalize_model(model: str) -> str:
    """Normalize deprecated model names to current active Gemini models."""
    if not model or 'gemini-1.' in model or 'gemini-2.' in model:
        return DEFAULT_ACTIVE_MODEL
    return model


def _get_client(api_key: str):
    """Create a Gemini client."""
    from google import genai
    return genai.Client(api_key=api_key)


def _generate_with_retry(
    api_key: str,
    model: str,
    prompt: str,
    max_retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Generate content from Gemini with retry and model fallback logic."""
    last_error = None
    active_model = _normalize_model(model)

    for attempt in range(max_retries):
        try:
            client = _get_client(api_key)

            # Try new SDK style first (google-genai 2.x)
            try:
                from google.genai import types
                response = client.models.generate_content(
                    model=active_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )
            except (ImportError, AttributeError, TypeError):
                # Fallback: try older SDK pattern
                from google import genai as genai_module
                model_obj = genai_module.GenerativeModel(active_model)
                response = model_obj.generate_content(prompt)

            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()

            # Handle candidates-based response
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    parts = candidate.content.parts
                    if parts:
                        return ''.join(p.text for p in parts if hasattr(p, 'text')).strip()

            return ''

        except Exception as e:
            error_str = str(e)
            last_error = e
            logger.warning(f'Gemini attempt {attempt + 1} ({active_model}) failed: {error_str[:200]}')

            # Handle model not found (404) by falling back to supported model
            if ('404' in error_str or 'NOT_FOUND' in error_str or 'not found' in error_str.lower()):
                switched = False
                for fb in FALLBACK_MODELS:
                    if fb != active_model:
                        logger.info(f'Switching model from {active_model} to fallback {fb}')
                        active_model = fb
                        switched = True
                        break
                if switched:
                    continue

            is_retryable = any(err in error_str for err in RETRYABLE_ERRORS)
            if is_retryable and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1.5
                logger.info(f'Retrying in {wait_time:.1f}s...')
                time.sleep(wait_time)
            else:
                break

    if last_error:
        raise last_error
    return ''


def check_api_key(api_key: str) -> dict:
    """Check if the Gemini API key is valid."""
    if not api_key or api_key in ('your_gemini_api_key_here', 'test-key-do-not-use', ''):
        return {'valid': False, 'error': 'API key not configured'}
    try:
        client = _get_client(api_key)
        models = list(client.models.list())
        return {'valid': True, 'model_count': len(models)}
    except Exception as e:
        return {'valid': False, 'error': str(e)[:200]}


def generate_rag_answer(
    api_key: str,
    model: str,
    question: str,
    context_chunks: list,
    conversation_history: list = None,
    document_title: str = '',
) -> dict:
    """Generate a RAG-grounded answer using Gemini."""
    if not context_chunks:
        return {
            'answer': 'I could not find relevant information in the uploaded document to answer this question. '
                      'Please make sure the document has been processed successfully.',
            'suggested_questions': [],
            'raw_citations': [],
        }

    # Build context with source labels
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        page = chunk.get('page_number', '?')
        doc_title = chunk.get('document_title', document_title or 'Document')
        context_parts.append(
            f'[Source {i} | Page {page} | "{doc_title}"]\n{chunk["content"]}'
        )
    context_str = '\n\n---\n\n'.join(context_parts)

    # Build conversation history
    history_str = ''
    if conversation_history:
        recent = conversation_history[-6:]
        for msg in recent:
            role = 'User' if msg.get('role') == 'user' else 'Assistant'
            history_str += f'{role}: {msg["content"][:500]}\n'

    prompt = f"""You are Scholar AI, an expert academic research assistant.
Answer the user's question based STRICTLY on the provided research paper excerpts.

RESEARCH PAPER EXCERPTS:
{context_str}

{"CONVERSATION HISTORY:" + chr(10) + history_str if history_str else ""}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer based ONLY on the provided excerpts. Do not fabricate information.
2. Use clear, academic language. Cite sources using [Source N] notation.
3. If the excerpts don't contain enough information, say so explicitly.
4. Use markdown for structure (bold, lists, headers).
5. After your main answer, list 3 relevant follow-up questions.

FORMAT:
ANSWER:
[Your detailed, well-cited answer]

FOLLOW-UP QUESTIONS:
1. [Question 1]
2. [Question 2]
3. [Question 3]"""

    raw_text = _generate_with_retry(api_key, model, prompt, temperature=0.2, max_tokens=2048)

    # Parse answer and follow-ups
    answer = raw_text
    follow_ups = []

    if 'FOLLOW-UP QUESTIONS:' in raw_text:
        parts = raw_text.split('FOLLOW-UP QUESTIONS:', 1)
        answer_part = parts[0]
        if 'ANSWER:' in answer_part:
            answer_part = answer_part.split('ANSWER:', 1)[1]
        answer = answer_part.strip()

        import re
        fuq_text = parts[1].strip()
        fuqs = re.findall(r'\d+\.\s+(.+)', fuq_text)
        follow_ups = [q.strip() for q in fuqs if q.strip()][:3]
    elif 'ANSWER:' in raw_text:
        answer = raw_text.split('ANSWER:', 1)[1].strip()

    return {
        'answer': answer or raw_text,
        'suggested_questions': follow_ups,
        'raw_citations': context_chunks,
    }


def generate_summary(
    api_key: str,
    model: str,
    document_title: str,
    text_chunks: list,
    summary_type: str = 'detailed',
) -> dict:
    """Generate a structured paper summary."""
    # Defensively handle both string and dict chunks
    clean_chunks = [t if isinstance(t, str) else t.get('content', '') for t in text_chunks[:30]]
    combined_text = '\n\n'.join(clean_chunks)[:15000]

    length_instruction = {
        'short': 'Provide a concise executive summary (200-300 words total).',
        'detailed': 'Provide comprehensive coverage of each section (500-1500 words total).',
        'section_wise': 'Provide thorough section-by-section analysis (1000-2000 words total).',
    }.get(summary_type, 'Provide a detailed summary.')

    prompt = f"""You are Scholar AI. Analyze this research paper and generate a structured summary.

PAPER TITLE: {document_title}
PAPER CONTENT:
{combined_text}

{length_instruction}

Provide the summary in this EXACT JSON format (respond ONLY with valid JSON, no extra text):
{{
  "executive_summary": "Brief 2-3 sentence overview",
  "abstract_summary": "Summary of abstract/overview",
  "research_objectives": "What the paper aims to achieve",
  "methodology": "Research methods and approaches",
  "dataset": "Datasets or data sources used",
  "experimental_setup": "Experimental design and tools",
  "main_findings": "Primary results and discoveries",
  "key_contributions": "Main contributions to the field",
  "limitations": "Acknowledged limitations",
  "conclusion": "Summary of conclusions",
  "future_work": "Future research directions mentioned"
}}"""

    raw = _generate_with_retry(api_key, model, prompt, temperature=0.1, max_tokens=3000)

    import json, re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            structured = json.loads(json_match.group())
            content = '\n\n'.join(
                f'**{k.replace("_", " ").title()}**\n\n{v}'
                for k, v in structured.items() if v and str(v).strip()
            )
            return {'content': content, 'structured_data': structured}
        except json.JSONDecodeError:
            pass

    return {'content': raw, 'structured_data': None}


def generate_comparison(
    api_key: str,
    model: str,
    papers: list,
) -> dict:
    """Generate a multi-paper comparison."""
    paper_sections = []
    for i, paper in enumerate(papers, 1):
        chunks_text = '\n'.join(paper.get('chunks', [])[:15])[:7000]
        paper_sections.append(f'PAPER {i}: {paper["title"]}\n{chunks_text}')

    combined = '\n\n' + ('=' * 60 + '\n\n').join(paper_sections)

    prompt = f"""You are Scholar AI. Compare these research papers comprehensively.

{combined}

Provide a structured comparison in EXACT JSON format (respond ONLY with valid JSON):
{{
  "overview": "Brief overview of all papers",
  "research_objectives": {{"similarities": "...", "differences": "..."}},
  "methodologies": {{"similarities": "...", "differences": "..."}},
  "datasets": {{"similarities": "...", "differences": "..."}},
  "evaluation_metrics": {{"similarities": "...", "differences": "..."}},
  "results": {{"similarities": "...", "differences": "..."}},
  "contributions": "Key contributions of each paper",
  "strengths_weaknesses": "Strengths and limitations of each paper",
  "common_themes": ["theme1", "theme2"],
  "conflicting_findings": "Any contradictions between papers",
  "research_gaps": ["gap1", "gap2"],
  "recommendation": "Overall synthesis and insights"
}}"""

    raw = _generate_with_retry(api_key, model, prompt, temperature=0.1, max_tokens=4096)

    import json, re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            structured = json.loads(json_match.group())
            return {'structured_data': structured, 'raw': raw}
        except json.JSONDecodeError:
            pass

    return {'structured_data': None, 'raw': raw}


def generate_insights(
    api_key: str,
    model: str,
    document_title: str,
    text_sample: str,
) -> dict:
    """Generate research insights for a document."""
    prompt = f"""You are Scholar AI. Extract research insights from this paper.

PAPER TITLE: {document_title}
CONTENT SAMPLE:
{text_sample[:12000]}

Provide insights in EXACT JSON format (respond ONLY with valid JSON):
{{
  "research_themes": ["theme1", "theme2", "theme3"],
  "key_concepts": ["concept1", "concept2", "concept3", "concept4", "concept5"],
  "main_findings": ["finding1", "finding2", "finding3"],
  "technical_terminology": ["term1: definition", "term2: definition"],
  "methodology_insights": "Analysis of methodological approach",
  "research_gaps": ["gap1", "gap2"],
  "potential_applications": ["application1", "application2"],
  "significance": "Why this research matters"
}}"""

    raw = _generate_with_retry(api_key, model, prompt, temperature=0.1, max_tokens=2048)

    import json, re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            structured = json.loads(json_match.group())
            return {'structured_data': structured, 'raw': raw}
        except json.JSONDecodeError:
            pass

    return {'structured_data': None, 'raw': raw}
