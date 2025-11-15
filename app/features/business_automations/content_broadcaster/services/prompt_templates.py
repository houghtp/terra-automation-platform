"""
Default AI prompt templates and metadata for the Content Broadcaster slice.

These definitions are used to seed system prompts on demand so that every
environment has a baseline template which can then be customised through the
AI Prompt manager. Each entry includes optional variable metadata that the UI
can use to render simple controls (sliders, selects, etc.).
"""

from __future__ import annotations

PromptDefinition = dict[str, object]

PROMPT_DEFAULTS: dict[str, PromptDefinition] = {
    "seo_blog_generation": {
        "name": "SEO Blog Post Generation",
        "description": "Creates a long-form, SEO optimised article from the plan inputs.",
        "category": "content_generation",
        "prompt_template": """You are a senior SEO content strategist. Generate a ready-to-publish blog post.

Adjust your writing style based on these user preferences:
- Professionalism level (1 low, 5 high): {{ professionalism_level }}
- Creativity level (1 safe, 5 bold): {{ creativity_level }}
- Subtle humour level (0 none, 5 playful): {{ humor_level }}

Topic: {{ title }}
Tone: {{ tone }}
Target audience: {{ target_audience or "general readers" }}
User description: {{ description or "No additional guidance provided." }}
Primary keywords: {{ keywords or "None provided" }}

{% if has_seo_analysis %}
### Competitor Insights (summarised)
{{ seo_analysis }}
{% endif %}

{% if previous_content %}
### Previous Draft (for reference / improvement)
{{ previous_content }}
{% endif %}

{% if validation_feedback %}
### SEO Validator Feedback to Address
{{ validation_feedback }}
{% endif %}

### Requirements
1. Produce a complete article of at least 1,600 words with H1/H2/H3 hierarchy.
2. Incorporate the target keywords naturally and provide additional LSI terms.
3. Include a table of contents, bulleted takeaways, and a compelling CTA.
4. Add an FAQ section answering 4+ questions.
5. Reference 2-3 authoritative external sources and propose internal link ideas.
6. Return Markdown formatted content ready for publishing.

Begin with an engaging introduction that matches the requested style and proceed with the full article.""",
        "required_variables": {
            "title": {"type": "string", "description": "Blog topic or title"},
        },
        "optional_variables": {
            "description": {"type": "string", "default": "", "description": "Additional guidance from the user"},
            "target_audience": {"type": "string", "default": "", "description": "Intended audience"},
            "keywords": {"type": "string", "default": "", "description": "CSV of key phrases"},
            "seo_analysis": {"type": "string", "default": "", "description": "Competitor research summary"},
            "previous_content": {"type": "string", "default": "", "description": "Draft content for refinement"},
            "validation_feedback": {"type": "string", "default": "", "description": "Feedback from validator"},
            "tone": {"type": "string", "default": "professional"},
            "professionalism_level": {
                "type": "integer",
                "default": 4,
                "description": "Formality of language",
                "ui": {"control": "slider", "label": "Professionalism", "min": 1, "max": 5, "step": 1},
            },
            "creativity_level": {
                "type": "integer",
                "default": 3,
                "description": "Playfulness and novelty",
                "ui": {"control": "slider", "label": "Creativity", "min": 1, "max": 5, "step": 1},
            },
            "humor_level": {
                "type": "integer",
                "default": 1,
                "description": "Degree of light humour",
                "ui": {"control": "slider", "label": "Humour", "min": 0, "max": 5, "step": 1},
            },
        },
    },
    "seo_competitor_analysis": {
        "name": "Competitor SEO Analysis",
        "description": "Summarises competitor content and highlights SEO opportunities.",
        "category": "seo_analysis",
        "prompt_template": """You are an advanced SEO strategist. Analyse the following competitor content and produce a structured report.

Depth of insight requested (1 = light, 5 = extensive): {{ analysis_depth }}

### Articles to Analyse
{{ combined_content }}

### Deliverables
1. Keyword Insights – primary, secondary, LSI keywords plus long-tail opportunities.
2. Content Structure – headings, suggested questions, readability observations.
3. Schema & Metadata – missing structured data, meta title/description improvements.
4. Internal/External Links – opportunities for internal clustering and authority citations.
5. Engagement – interactive elements, multimedia, suggestions to improve dwell time.
6. On-Page Technicals – page speed, mobile friendliness hints, canonical/URL structure.

Return a concise, sectioned report in Markdown with actionable recommendations suitable for briefing an AI writer.""",
        "required_variables": {
            "combined_content": {"type": "string", "description": "Concatenated competitor articles"},
        },
        "optional_variables": {
            "analysis_depth": {
                "type": "integer",
                "default": 4,
                "description": "Granularity of recommendations",
                "ui": {"control": "slider", "label": "Analysis Depth", "min": 1, "max": 5, "step": 1},
            }
        },
    },
    "seo_content_validation": {
        "name": "SEO Content Validator",
        "description": "Scores generated content and provides improvement suggestions.",
        "category": "refinement",
        "prompt_template": """You are an SEO quality control specialist. Review the blog post below and respond with JSON containing a score and actionable feedback.

Content title: {{ title }}
Target score: {{ target_score }}
Strictness level (1 lenient, 5 very strict): {{ strictness_level }}

### Blog Post
{{ content }}

Respond with JSON:
{
  "score": <0-100>,
  "status": "PASS|FAIL",
  "issues": ["issue 1", "issue 2"],
  "recommendations": ["action 1", "action 2"],
  "strengths": ["strength 1"]
}

PASS if score >= target_score, otherwise FAIL.""",
        "required_variables": {
            "title": {"type": "string"},
            "content": {"type": "string"},
        },
        "optional_variables": {
            "target_score": {"type": "integer", "default": 95, "description": "Score threshold for PASS"},
            "strictness_level": {
                "type": "integer",
                "default": 4,
                "description": "Severity of scoring",
                "ui": {"control": "slider", "label": "Strictness", "min": 1, "max": 5, "step": 1},
            },
        },
    },
    "channel_variant_twitter": {
        "name": "Twitter Variant",
        "description": "Creates a concise post tailored for Twitter/X.",
        "category": "channel_adaptation",
        "prompt_template": """Create an engaging Twitter/X post from the content below.

Professionalism level: {{ professionalism_level }}
Humour level: {{ humor_level }}

Constraints:
- Maximum characters: {{ constraints.max_chars }}
- Format: {{ constraints.format }}
- Tone: {{ constraints.tone }}

Original title: {{ title }}

Original content (excerpt):
{{ content[:1200] }}

Return copy only (no explanations) that fits within the character limit and includes relevant hashtags.""",
        "required_variables": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "constraints": {"type": "object"},
        },
        "optional_variables": {
            "professionalism_level": {"type": "integer", "default": 4},
            "humor_level": {"type": "integer", "default": 1},
        },
    },
    "channel_variant_linkedin": {
        "name": "LinkedIn Variant",
        "description": "Produces a professional LinkedIn-ready post.",
        "category": "channel_adaptation",
        "prompt_template": """Create a LinkedIn post derived from the content below. Keep it informative, encourage discussion, and match the requested professionalism level {{ professionalism_level }}.

Original title: {{ title }}

Constraints:
- Maximum characters: {{ constraints.max_chars }}
- Format: {{ constraints.format }}
- Tone guidance: {{ constraints.tone }}

Original content (excerpt):
{{ content[:1500] }}

Return a LinkedIn post only (no explanations) with paragraphs, emojis used sparingly, and a call-to-action question at the end.""",
        "required_variables": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "constraints": {"type": "object"},
        },
        "optional_variables": {
            "professionalism_level": {"type": "integer", "default": 4},
        },
    },
    "channel_variant_medium": {
        "name": "Medium Variant",
        "description": "Adapts the blog into a Medium-style narrative article.",
        "category": "channel_adaptation",
        "prompt_template": """Rewrite the content below into a Medium article with storytelling flair matched to creativity level {{ creativity_level }}.

Original title: {{ title }}

Constraints:
- Format: {{ constraints.format }}

Original content:
{{ content }}

Return Markdown formatted content suitable for Medium, including a short hook, subheadings, and a closing section inviting reader engagement.""",
        "required_variables": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "constraints": {"type": "object"},
        },
        "optional_variables": {
            "creativity_level": {"type": "integer", "default": 3},
        },
    },
    "channel_variant_wordpress": {
        "name": "WordPress Variant",
        "description": "Formats the content for WordPress with HTML structure.",
        "category": "channel_adaptation",
        "prompt_template": """Transform the following content into clean HTML ready for WordPress. Maintain the requested professionalism level {{ professionalism_level }}.

Title: {{ title }}

Output Requirements:
- Use semantic HTML (h2/h3, lists, blockquotes where appropriate)
- Include a short intro, key takeaways list, and conclusion
- Wrap FAQs in a <section> with question headings

Original content:
{{ content }}

Return HTML only, no explanations.""",
        "required_variables": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "constraints": {"type": "object"},
        },
        "optional_variables": {
            "professionalism_level": {"type": "integer", "default": 4},
        },
    },
    "channel_variant_facebook": {
        "name": "Facebook Variant",
        "description": "Generates a friendly Facebook post with optional emojis.",
        "category": "channel_adaptation",
        "prompt_template": """Create a Facebook post from the following content. Humour level: {{ humor_level }} (0 none, 5 playful).

Title: {{ title }}

Constraints:
- Character budget: {{ constraints.max_chars }}
- Tone guidance: {{ constraints.tone }}

Original content (excerpt):
{{ content[:1500] }}

Return a Facebook-ready post with short paragraphs, emojis if appropriate, and a clear CTA inviting comments or shares.""",
        "required_variables": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "constraints": {"type": "object"},
        },
        "optional_variables": {
            "humor_level": {"type": "integer", "default": 2},
        },
    },
}
