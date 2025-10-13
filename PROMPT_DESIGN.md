# RAG Enterprise - Improved Prompt Design

## Overview

The system prompt has been redesigned to **strictly enforce knowledge base boundaries** while maintaining conversational ability. This prevents the LLM from hallucinating or using general knowledge outside the retrieved context.

---

## New Prompt Structure

### Critical Rules (NEVER VIOLATED)

1. **ONLY answer using information from the Context**
2. **If Context doesn't contain the answer → "I don't have that information in the knowledge base."**
3. **NEVER use general knowledge or training data**
4. **NEVER make assumptions or infer information not in Context**
5. **NEVER provide advice/recommendations unless explicitly in Context**

### Allowed Behaviors

✓ Answer questions directly from Context  
✓ Combine information from multiple Context sections  
✓ Clarify or rephrase Context information  
✓ Ask for clarification if question is ambiguous  
✓ Admit when Context doesn't contain enough info  
✓ Quote relevant sections when helpful  
✓ Be conversational and helpful in tone  

### Response Guidelines

- **Direct answers first** when possible
- **Cite sources**: mention which document/section
- **Partial answers**: provide what you know, then state what's missing
- **Greetings/small-talk**: respond briefly, redirect to knowledge base topics
- **Out-of-scope questions**: politely decline, redirect to available topics

---

## Example Behaviors

### ✅ GOOD: Answers from Context

**Query**: "What is the PTO policy?"  
**Context**: Contains PTO policy document  
**Response**: "According to the Employee Handbook, employees receive 15 days of PTO annually..."

### ✅ GOOD: Admits Missing Information

**Query**: "What's the dress code for remote workers?"  
**Context**: Only has office dress code policy  
**Response**: "I have information about the office dress code, but I don't have specific information about dress code for remote workers in the knowledge base."

### ✅ GOOD: Partial Answer with Honesty

**Query**: "How do I request vacation and sick leave?"  
**Context**: Contains vacation request process, but no sick leave info  
**Response**: "For vacation requests, you need to submit a request through the HR portal at least 2 weeks in advance. However, I don't have information about sick leave procedures in the knowledge base."

### ✅ GOOD: Handles Greetings

**Query**: "Hello! How are you?"  
**Response**: "Hello! I'm here to help you find information from the company knowledge base. What would you like to know about our policies, procedures, or documentation?"

### ❌ BAD: General Knowledge (OLD BEHAVIOR)

**Query**: "What is Python?"  
**Context**: No Python documentation  
**Old Response**: "Python is a high-level programming language..." ❌  
**New Response**: "I don't have information about Python in the knowledge base. I can only answer questions about the company documentation available to me."

### ❌ BAD: Assumptions (OLD BEHAVIOR)

**Query**: "Should I use vacation days for a doctor's appointment?"  
**Context**: Only has vacation policy basics  
**Old Response**: "It depends on company policy, typically short appointments..." ❌  
**New Response**: "I don't have specific information about using vacation days for medical appointments in the knowledge base. You may want to check with HR for guidance on this."

---

## Technical Implementation

**Location**: `backend/llm_client.py` → `_build_prompt()` method

**Key Changes**:
1. Explicit instruction hierarchy (CRITICAL RULES → ALLOWED → GUIDELINES)
2. Multiple examples of when to say "I don't know"
3. Clear boundaries between Context and general knowledge
4. Conversational tone maintained within boundaries

**Prompt Length**: ~500 tokens (reasonable overhead for 4K context window)

---

## Testing Scenarios

### Test 1: In-Scope Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What embedding model is used in this system?"}'
```
**Expected**: Answer from `rag_system_architecture.txt` (BGE-Large-En-v1.5)

### Test 2: Out-of-Scope Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?"}'
```
**Expected**: "I don't have that information in the knowledge base."

### Test 3: Partially Answered Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about Milvus and PostgreSQL in this system"}'
```
**Expected**: Info about Milvus from docs, admits no PostgreSQL info

### Test 4: Conversational Query
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Hi! Can you help me understand the architecture?"}'
```
**Expected**: Friendly response, then provides architecture info from context

---

## Benefits

### 1. Eliminates Hallucinations
- LLM cannot invent information not in Context
- Reduces liability and misinformation risk

### 2. Maintains Trust
- Users know responses are **backed by actual documentation**
- Source attribution builds confidence

### 3. Conversational Yet Bounded
- Handles greetings and follow-ups naturally
- Redirects gracefully to knowledge base topics

### 4. Clear User Expectations
- "I don't know" responses signal knowledge base gaps
- Encourages users to add missing documentation

### 5. Audit-Friendly
- Every response traceable to source documents
- Compliance-friendly for regulated industries

---

## Prompt Engineering Best Practices Applied

1. **Hierarchy of Instructions**: Critical rules first, then allowed behaviors
2. **Explicit Constraints**: Use NEVER/MUST for hard boundaries
3. **Positive Examples**: Show what TO do, not just what NOT to do
4. **Escape Hatches**: Provide templates for "I don't know" scenarios
5. **Role Definition**: Clear identity as "enterprise knowledge base assistant"
6. **Output Format**: Structured response with citations

---

## Future Enhancements

### Short-term (Next Sprint)
- [ ] Add "related topics" suggestions when answering
- [ ] Include relevance scores in citations
- [ ] Multi-turn context: remember previous Q&A in session

### Medium-term (Next Quarter)
- [ ] Intent classification: route questions to appropriate document sets
- [ ] Confidence scoring: flag low-confidence answers
- [ ] User feedback loop: thumbs up/down to improve retrieval

### Long-term (Next Year)
- [ ] Fine-tune model on enterprise Q&A pairs
- [ ] Custom system prompts per document type
- [ ] Multi-language support with translated prompts

---

## Monitoring & Metrics

### Track These Metrics
1. **"I don't know" rate**: Should be 10-20% (healthy boundary setting)
2. **Citation accuracy**: Do cited sources actually contain the answer?
3. **User satisfaction**: Thumbs up/down feedback
4. **Follow-up rate**: Do users need clarifications?

### Red Flags
- "I don't know" rate > 40%: Retrieval quality issue
- "I don't know" rate < 5%: May be hallucinating
- Many follow-ups: Answers may be unclear

---

## Configuration

The prompt is **hard-coded** in `llm_client.py` for consistency. To customize:

1. Edit `backend/llm_client.py` → `_build_prompt()` method
2. Adjust CRITICAL RULES for your use case
3. Test thoroughly with edge cases
4. Rebuild backend: `docker compose build backend`
5. Restart: `docker compose up -d backend`

**Do NOT** make prompt configurable via environment variables - this risks prompt injection attacks.

---

## Conclusion

The new prompt design ensures:
- ✅ **Zero hallucinations** from general knowledge
- ✅ **Conversational** but bounded interactions
- ✅ **Clear citations** to source documents
- ✅ **Honest "I don't know"** when appropriate
- ✅ **Production-ready** for enterprise deployment

This is a **critical security and quality control** measure for RAG systems.

---

**Last Updated**: October 14, 2025  
**Author**: Engineering Team  
**Version**: 2.0  
