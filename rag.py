"""
Simplified RAG implementation for the Azure Function App
"""

def chunk_content(content_json, chunk_size=1500, overlap=300):
    """
    Chunks the content from a Document Intelligence result
    """
    full_text = content_json['content']
    spans = content_json['pages']

    chunks = []
    start = 0
    chunk_id = 0

    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        chunk_text = full_text[start:end]

        # Determine overlapping page numbers
        overlapping_pages = set()
        for page in spans:
            if 'spans' in page and page['spans']:
                page_start = page['spans'][0]['offset']
                page_end = page_start + page['spans'][0]['length']
                if start < page_end and end > page_start:
                    overlapping_pages.add(page['pageNumber'])

        chunks.append({
            'chunk_id': chunk_id,
            'content': chunk_text,
            'page_numbers': sorted(overlapping_pages),
        })

        chunk_id += 1
        # Move start forward with overlap
        start += chunk_size - overlap

    return chunks


def rag_pipeline(content_json, query, max_chunks=10):
    """
    Simplified RAG pipeline that just divides content into chunks and returns relevant ones
    based on basic text search. In a production environment, this should be replaced
    with proper vector search using embeddings.
    """
    chunks = chunk_content(content_json)
    
    # Score each chunk based on keyword presence (simplified approach)
    scored_chunks = []
    query_terms = query.lower().split()
    
    for chunk in chunks:
        score = sum(chunk['content'].lower().count(term) for term in query_terms)
        scored_chunks.append((score, chunk))
    
    # Sort by score and take top chunks
    scored_chunks.sort(reverse=True)
    top_chunks = scored_chunks[:max_chunks]
    
    # Format output
    context = ""
    for _, chunk in top_chunks:
        context += f"### Page Numbers: {chunk['page_numbers']}\n{chunk['content']}\n\n"
    
    return context