"""
AI Prompts for High-Quality Learning Material Generation
Optimized prompts for generating accurate, educational content
"""

# ============================================================================
# Learning Material Analysis
# ============================================================================

LEARNING_MATERIAL_ANALYSIS_PROMPT = """
You are an expert educational content analyzer. Analyze the following learning material and extract comprehensive information.

Material:
{content}

Provide a detailed analysis in the following JSON format:
{{
    "title": "Accurate, concise title (max 10 words)",
    "description": "Brief 2-3 sentence description of the material",
    "executive_summary": "Executive summary in 3-5 sentences",
    "bullet_summary": "5-7 bullet points summarizing key concepts",
    "key_concepts": ["List of 5-10 key concepts"],
    "important_formulas": [
        {{
            "formula": "Mathematical representation",
            "description": "What the formula represents",
            "variables": "Explanation of variables"
        }}
    ] if applicable,
    "keywords": ["List of 15-20 relevant keywords"],
    "definitions": [
        {{
            "term": "Term",
            "definition": "Clear definition"
        }}
    ],
    "important_dates": [
        {{
            "date": "Date",
            "event": "Event description",
            "significance": "Why it matters"
        }}
    ] if applicable,
    "important_people": [
        {{
            "name": "Name",
            "contribution": "Their contribution",
            "significance": "Why they matter"
        }}
    ] if applicable,
    "difficult_concepts": ["List of 3-5 most difficult concepts"],
    "easy_concepts": ["List of 3-5 easiest concepts"],
    "common_mistakes": [
        {{
            "mistake": "Common mistake students make",
            "correction": "How to avoid it"
        }}
    ],
    "exam_tips": ["5-7 exam preparation tips"],
    "real_world_examples": [
        {{
            "example": "Real-world application",
            "explanation": "How it connects to theory"
        }}
    ]
}}

Ensure all information is accurate, educational, and suitable for university-level study.
Be concise but complete. Avoid duplicate information.
"""


# ============================================================================
# Flashcard Generation
# ============================================================================

FLASHCARD_GENERATION_PROMPT = """
You are an expert educational content creator. Generate high-quality flashcards from the following learning material.

Material:
{content}

Generate 10-15 flashcards covering the most important concepts. Each flashcard should test understanding, not just memorization.

Provide flashcards in the following JSON format:
{{
    "flashcards": [
        {{
            "front": "Clear question or prompt",
            "back": "Comprehensive answer with explanation",
            "difficulty": "easy|medium|hard",
            "topic": "Main topic being tested",
            "explanation": "Brief explanation of why this is important",
            "tags": ["tag1", "tag2"]
        }}
    ]
}}

Guidelines:
- Mix of question types: definitions, applications, comparisons, problem-solving
- Front should be clear and specific
- Back should provide complete answer with context
- Include a mix of easy, medium, and hard difficulty
- Each flashcard should test a different concept
- Avoid yes/no questions
- Focus on understanding over rote memorization
- Include application questions where possible
"""


# ============================================================================
# Quiz Generation
# ============================================================================

QUIZ_GENERATION_PROMPT = """
You are an expert educational assessment creator. Generate exam-quality quiz questions from the following learning material.

Material:
{content}

Generate 10-15 varied quiz questions to test understanding. Mix different question types.

Provide questions in the following JSON format:
{{
    "questions": [
        {{
            "type": "multiple_choice|true_false|fill_in_blank|short_answer|scenario",
            "question": "Clear question text",
            "options": ["A", "B", "C", "D"] if multiple choice,
            "correct_answer": "Correct answer",
            "explanation": "Detailed explanation of why this is correct",
            "difficulty": "easy|medium|hard",
            "topic": "Main topic being tested",
            "learning_objective": "What this question tests"
        }}
    ]
}}

Guidelines:
- Include 4-5 multiple choice questions
- Include 2-3 true/false questions
- Include 2-3 fill-in-the-blank questions
- Include 2-3 short answer questions
- Include 1-2 scenario-based application questions
- Questions should test different cognitive levels: recall, understanding, application
- Multiple choice options should be plausible but clearly distinguishable
- Explanations should help students learn from mistakes
- Include a mix of easy, medium, and hard questions
- Avoid ambiguous questions
- Test understanding, not just memorization
"""


# ============================================================================
# Mindmap Generation
# ============================================================================

MINDMAP_GENERATION_PROMPT = """
You are an expert educational content organizer. Create a structured mindmap from the following learning material.

Material:
{content}

Create a hierarchical mindmap showing relationships between concepts.

Provide mindmap in the following JSON format:
{{
    "main_topic": "Central theme",
    "branches": [
        {{
            "name": "Branch name",
            "sub_branches": [
                {{
                    "name": "Sub-branch name",
                    "concepts": ["concept1", "concept2", "concept3"]
                }}
            ]
        }}
    ],
    "relationships": [
        {{
            "from": "Concept A",
            "to": "Concept B",
            "type": "causes|relates to|is part of|leads to",
            "description": "Brief description of relationship"
        }}
    ]
}}

Guidelines:
- Main topic should be the central theme
- Create 4-6 main branches covering major themes
- Each branch should have 2-4 sub-branches
- Include 3-5 concepts per sub-branch
- Show relationships between related concepts
- Structure should be logical and hierarchical
- Use clear, concise labels
- Include cross-connections where appropriate
"""


# ============================================================================
# Keywords Generation
# ============================================================================

KEYWORDS_GENERATION_PROMPT = """
You are an expert educational content analyzer. Extract and generate relevant keywords from the following learning material.

Material:
{content}

Generate 20-25 relevant keywords that would be useful for search, tagging, and study organization.

Provide keywords in the following JSON format:
{{
    "keywords": [
        {{
            "keyword": "keyword",
            "definition": "Brief definition",
            "importance": "high|medium|low"
        }}
    ]
}}

Guidelines:
- Include key terms from the material
- Include related concepts
- Include important people, dates, events if applicable
- Include technical terms and jargon
- Mark importance based on centrality to the material
- Definitions should be concise
- Avoid overly generic terms
"""


# ============================================================================
# Summary Generation
# ============================================================================

SUMMARY_GENERATION_PROMPT = """
You are an expert educational content summarizer. Create a comprehensive summary of the following learning material.

Material:
{content}

Create a summary that captures all essential information while being concise.

Provide summary in the following JSON format:
{{
    "summary": "Comprehensive 3-5 paragraph summary",
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3",
        "Key point 4",
        "Key point 5"
    ],
    "takeaways": [
        "Main takeaway 1",
        "Main takeaway 2",
        "Main takeaway 3"
    ]
}}

Guidelines:
- Summary should be 3-5 paragraphs
- Cover all major concepts
- Be concise but complete
- Use clear, accessible language
- Focus on what students need to remember
- Include 5 key points
- Include 3 main takeaways
"""


# ============================================================================
# Revision Notes Generation
# ============================================================================

REVISION_NOTES_GENERATION_PROMPT = """
You are an expert educational content creator. Create comprehensive revision notes from the following learning material.

Material:
{content}

Create revision notes optimized for last-minute study and exam preparation.

Provide revision notes in the following JSON format:
{{
    "revision_notes": {{
        "title": "Title",
        "overview": "Brief overview",
        "key_concepts": [
            {{
                "concept": "Concept name",
                "explanation": "Clear explanation",
                "importance": "Why it matters"
            }}
        ],
        "formulas": [
            {{
                "formula": "Formula",
                "when_to_use": "When to apply this formula",
                "example": "Example usage"
            }}
        ] if applicable,
        "mnemonics": [
            {{
                "mnemonic": "Memory aid",
                "what_it_helps": "What it helps remember"
            }}
        ],
        "exam_tips": [
            "Tip 1",
            "Tip 2",
            "Tip 3"
        ],
        "common_mistakes": [
            {{
                "mistake": "Common mistake",
                "how_to_avoid": "Prevention strategy"
            }}
        ],
        "quick_reference": "Bullet-point quick reference sheet"
    }}
}}

Guidelines:
- Focus on exam-relevant information
- Include memory aids (mnemonics)
- Highlight common mistakes and how to avoid them
- Include practical exam tips
- Create a quick reference section
- Be concise and scannable
- Use formatting that's easy to review quickly
"""


# ============================================================================
# Prompt Builder
# ============================================================================

class PromptBuilder:
    """Helper class to build prompts with content."""
    
    @staticmethod
    def build_analysis_prompt(content: str) -> str:
        """Build the learning material analysis prompt."""
        return LEARNING_MATERIAL_ANALYSIS_PROMPT.format(content=content[:10000])
    
    @staticmethod
    def build_flashcard_prompt(content: str) -> str:
        """Build the flashcard generation prompt."""
        return FLASHCARD_GENERATION_PROMPT.format(content=content[:8000])
    
    @staticmethod
    def build_quiz_prompt(content: str) -> str:
        """Build the quiz generation prompt."""
        return QUIZ_GENERATION_PROMPT.format(content=content[:8000])
    
    @staticmethod
    def build_mindmap_prompt(content: str) -> str:
        """Build the mindmap generation prompt."""
        return MINDMAP_GENERATION_PROMPT.format(content=content[:8000])
    
    @staticmethod
    def build_keywords_prompt(content: str) -> str:
        """Build the keywords generation prompt."""
        return KEYWORDS_GENERATION_PROMPT.format(content=content[:8000])
    
    @staticmethod
    def build_summary_prompt(content: str) -> str:
        """Build the summary generation prompt."""
        return SUMMARY_GENERATION_PROMPT.format(content=content[:10000])
    
    @staticmethod
    def build_revision_notes_prompt(content: str) -> str:
        """Build the revision notes generation prompt."""
        return REVISION_NOTES_GENERATION_PROMPT.format(content=content[:10000])
