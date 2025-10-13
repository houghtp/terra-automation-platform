import os
import pandas as pd
import openai
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
import json

# Load API Keys from Environment Variables
openai.api_key = os.getenv("OPENAI_API_KEY")
serpapi_key = os.getenv("SERPAPI_KEY")
scrapingdog_api_key = os.getenv("SCRAPINGDOG_API_KEY")
scrapingbee_api_key = os.getenv("SCRAPINGBEE_API_KEY")

if not openai.api_key:
    raise ValueError("⚠ OpenAI API key not found! Set OPENAI_API_KEY as an environment variable.")
if not serpapi_key:
    raise ValueError("⚠ SerpAPI key not found! Set SERPAPI_KEY as an environment variable.")

# Google Sheets Public URL
SPREADSHEET_ID = "1tZ4Cks8N6YcFstybuuHhswxfCIeKOFfACjZQXgIE1Fw"
SHEET_GID = "1314679421"
URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={SHEET_GID}"

# Read Titles from Google Sheets
df = pd.read_csv(URL)
titles = df.iloc[:, 3].dropna().tolist()

# Create Folder for Storing Results
output_directory = "blog_data"
os.makedirs(output_directory, exist_ok=True)

def get_top_google_results(query, num_results=5):
    url = f"https://api.scrapingdog.com/google?api_key={scrapingdog_api_key}&query={query}&num={num_results}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        results = response.json()
        top_results = [(res['title'], res['link']) for res in results.get("organic_results", [])[:num_results]]
        while len(top_results) < num_results:
            top_results.append(("No result found", "N/A"))
        return top_results
    except Exception as e:
        print(f"⚠ Failed to fetch results from Scrapingdog: {str(e)}")
        return [("Error fetching results", "N/A")] * num_results

def get_top_google_results_scrapingbee(query):
    url = "https://app.scrapingbee.com/api/v1/store/google"
    params = {
        'api_key': scrapingbee_api_key,
        'search': query,
        'language': 'en',
        'nb_results': '5',
        'country_code': 'gb'
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
        top_results = []
        for res in results.get("organic_results", []):
            title = res.get('title', 'No title available')
            url = res.get('url', 'No URL available')
            top_results.append((title, url))
        while len(top_results) < 5:
            top_results.append(("No result found", "N/A"))
        return top_results[:5]
    except requests.exceptions.HTTPError as e:
        print(f"⚠ HTTP Error: {e}")
        return [("Error fetching results", "N/A")] * 5
    except Exception as e:
        print(f"⚠ Failed to fetch results from Scrapingbee: {str(e)}")
        return [("Error fetching results", "N/A")] * 5

def scrape_article(url):
    if url == "N/A":
        return "⚠ No valid URL for this search result."

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract text from common content tags
        article_text = ""
        for tag in ["article", "div", "section"]:
            content = soup.find(tag)
            if content:
                article_text = content.get_text(separator="\n", strip=True)
                break 
        
        if not article_text:
            paragraphs = soup.find_all("p")
            article_text = "\n".join([p.get_text(strip=True) for p in paragraphs])

        return article_text if len(article_text) > 100 else "⚠ Could not extract meaningful content."
    
    except Exception as e:
        return f"⚠ Failed to scrape {url}: {str(e)}"

def analyze_competitor_content(combined_content):
    analysis_prompt = f"""
You are an advanced SEO strategist. Your task is to analyze the following articles and provide a structured SEO analysis.

### **Key SEO Areas to Analyze:**
#### **1. Keyword Optimization**
   - Identify **primary keywords**, **secondary keywords**, and **LSI (related) keywords**.
   - Suggest **long-tail queries** that could help rank in **Google's Featured Snippets**.
   - Compare keyword **density and placement** with top competitors.

#### **2. Content Structure & Readability**
   - Evaluate **H1, H2, H3 hierarchy** for clear sectioning.
   - Suggest **questions that could be H2s/H3s** to improve scannability.
   - Assess **sentence complexity (Flesch-Kincaid Score)** for readability.
   - Identify missing elements like **Table of Contents, jump links, and bulleted lists**.

#### **3. Headers & Schema Markup**
   - Identify whether **FAQ Schema, Recipe Schema, or HowTo Schema** is present.
   - Suggest **Google-approved JSON-LD structured data** improvements.
   - Ensure **Google Discover optimization** (e.g., Web Stories, short-form content).

#### **4. Internal & External Linking**
   - Identify **internal linking gaps** using **topic clusters**.
   - Recommend **external authority links** (e.g., BBC Good Food, AllRecipes).
   - Suggest **anchor text improvements** for better topic relevancy.

#### **5. Engagement & Interactive Elements**
   - Check for **star ratings, comment sections, and polls**.
   - Identify whether **videos, GIFs, or interactive elements** are used.
   - Suggest **ways to improve dwell time and reduce bounce rate**.

#### **6. On-Page SEO Optimization**
   - Assess **meta title & description** for CTR optimization.
   - Check **image alt text** and **file names** (e.g., "cottage_pie_recipe.jpg").
   - Evaluate **canonical tags, structured breadcrumbs, and URL structure**.

---
### **Content to Analyze:**
{combined_content}

### **Optimization Plan:**
Provide an **actionable improvement plan** covering all six SEO areas above.
- **List specific improvements**, including **example keyword placements**.
- Ensure **recommendations align with Google's ranking factors**.
- Suggest **automation-friendly optimizations** for AI-powered content creation.


"""

    response = openai.Client().chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert blog writer."},
            {"role": "user", "content": analysis_prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content

def generate_blog_post(title, seo_analysis, previous_blog_content=None, validation_feedback=None):
    blog_prompt = f"""
Title: {title}

You are an **expert SEO blog writer**. Your task is to produce a complete, ready-to-publish blog post that is 100% SEO optimized for the topic provided by the title above, using the latest SEO analysis and the provided validation feedback.

Please ensure that:
- The content is entirely on-topic and directly relevant to the title: "{title}".
- You generate detailed, actionable content with real-world advice, concrete steps, and measurable recommendations that a reader can immediately apply.
- The output is a fully written blog post, not just a list of suggestions or improvement tips.
- If there is any previous blog post content provided, retain and enhance its good elements while fixing only the identified SEO issues.
- Follow the mandatory SEO enhancements strictly to improve keyword optimization, content structure, schema markup, linking, engagement elements, and on-page/mobile SEO without removing any previous improvements.

---
### **SEO Analysis:**
{seo_analysis}

---
### **Previous Blog Post (Use this as the base and improve it)**
{previous_blog_content if previous_blog_content else "No previous version, this is the first draft."}

---
### **Validation Feedback (Fix these SEO issues only)**
{validation_feedback if validation_feedback else "No feedback yet. Optimize based on SEO best practices."}

---
## **Mandatory SEO Enhancements**
To **outperform competitors**, improve the blog using these advanced SEO tactics:

✅ **1. Keyword Optimization**
   - Ensure **primary and secondary keywords** are in **title, intro, headings, and alt text**.
   - Use **long-tail keyword variations** for **Google Featured Snippets**.
   - Maintain **proper keyword density** (avoid stuffing).
   - Integrate **LSI keywords** naturally.

✅ **2. Content Structure & Readability**
   - Follow an **H1 → H2 → H3 hierarchy**.
   - Add a **Table of Contents with jump links**.
   - Use **short paragraphs (2-3 sentences max) for scannability**.
   - Improve readability using **bulleted lists, numbered steps, key takeaways**.

✅ **3. Schema Markup & Metadata**
   - Implement **FAQ Schema, Recipe Schema, and HowTo Schema**.
   - Ensure **Google Discover best practices** for mobile-first ranking.
   - Add **Pinterest & Facebook metadata** for better social sharing.
   - Optimize **meta title and description (160 chars max, keyword-rich)**.

✅ **4. Internal & External Linking**
   - Add **3+ internal links** to related content.
   - Include **2+ external links** to authoritative sources (BBC Good Food, etc.).
   - Use **keyword-rich anchor text**.

✅ **5. Engagement & Interactive Elements**
   - Include **star ratings, polls, or interactive content**.
   - Add an **FAQ section** to capture **voice search & People Also Ask queries**.
   - Encourage user interaction (comments, sharing).
   - Embed **images, videos, or step-by-step visuals**.

✅ **6. On-Page SEO & Mobile Friendliness**
   - Ensure **title tag is compelling and keyword-rich**.
   - Optimize **image alt text** with **SEO-friendly filenames**.
   - Ensure the blog is **fast-loading & mobile-friendly (Core Web Vitals)**.
   - Implement **canonical tags to prevent duplicate content issues**.

---
- **Now, using the title "{title}" improve this blog post for maximum SEO performance.**
- **Produce a complete and cohesive blog post that is fully optimized for SEO and ready for immediate publication.**
- **Do not generate generic suggestions—deliver a finished blog post with all required content.**
- **Fix ONLY the missing SEO elements.**
- **Retain good elements from the previous version.**
- **Do not remove previous improvements.**
- **Make it engaging, informative, and actionable.**
- **Use a friendly and approachable tone.**
- **Avoid jargon and complex terms.**
- **Make it easy to read and understand.**
- **Use a conversational style.**
- **Use emojis to enhance engagement.**
"""
    
    response = openai.Client().chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": blog_prompt}]
    )
    return response.choices[0].message.content

def validate_blog_post(title, blog_content):

    validation_prompt = f"""
You are an **SEO quality control specialist** and **Google ranking expert**. Your task is to analyze the blog post below and assign an SEO **score from 0 to 100** based on compliance with key ranking factors.

### **Scoring Criteria (Total: 100 Points)**
✅ **1. Keyword Optimization (20 points)**
   - Are **primary and secondary keywords** naturally integrated into the **title, introduction, subheadings, and body text**?
   - Are **long-tail keyword variations** used effectively for **featured snippets**?
   - Does the blog avoid **keyword stuffing** while maintaining **optimal keyword density**?

✅ **2. Content Structure & Readability (15 points)**
   - Is the **H1, H2, and H3 hierarchy** correctly structured?
   - Does the blog include a **Table of Contents (TOC) with jump links** for better UX and Google crawling?
   - Are **paragraphs short and easy to skim** (2-3 sentences per paragraph)?
   - Are there **bulleted lists, numbered steps, and key takeaways** to enhance readability?

✅ **3. Schema Markup & Metadata (15 points)**
   - Does the blog **implement structured data (FAQ Schema, Recipe Schema, HowTo Schema, or JSON-LD)?**
   - Is the **meta title and meta description optimized for Google CTR** (contains target keywords & a CTA)?
   - Are **alt text and image file names optimized** for **Google Image Search**?
   - Does the blog have **Pinterest & Facebook metadata** for **social media sharing**?

✅ **4. Internal & External Links (15 points)**
   - Does the blog contain **at least 3 internal links** to related content for **topic authority**?
   - Are there **2+ external links** to **high-authority sources** (e.g., BBC Good Food, AllRecipes)?
   - Are the **internal & external links using descriptive, keyword-rich anchor text**?
   - Does the blog have **structured breadcrumbs** to improve crawlability?

✅ **5. Engagement & Interactive Elements (15 points)**
   - Does the blog include a **star rating system, voting, or poll** to increase CTR?
   - Is there an **FAQ section** to capture **voice search & "People Also Ask" queries**?
   - Does the blog **encourage user interaction** (e.g., comment section, share prompts)?
   - Does it include **interactive elements like videos, step-by-step images, or GIFs**?

✅ **6. On-Page SEO & Mobile Friendliness (20 points)**
   - Is the **title tag compelling, keyword-rich, and formatted for higher CTR**?
   - Is the **meta description under 160 characters with a strong call-to-action**?
   - Does the blog meet **Google Core Web Vitals** for fast loading and mobile-friendliness?
   - Are all **canonical tags properly set up** to prevent duplicate content issues?

---

### **Blog Content to Analyze:**
{blog_content}

---
### **Final Evaluation (Return as JSON Output)**

1️⃣ **Assign a numerical SEO Score (0-100).**  
2️⃣ **If the score is <100, return "FAIL" with missing SEO elements.**  
3️⃣ **If the score is 100, return "PASS".**  
4️⃣ **Format response as JSON:**

{{
   "title": "{title}",
   "score": 85,
   "status": "FAIL",
   "issues": ["Schema Markup", "Engagement"],
   "recommendations": {{
       "Schema Markup": {{ "issue": "...", "fix": "..." }},
       "Engagement": {{ "issue": "...", "fix": "..." }}
   }}
}}

"""

    response = openai.Client().chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": validation_prompt}]
    )

    # Extract response text and clean it
    raw_response = response.choices[0].message.content.strip()

    # Remove Markdown JSON formatting if present
    if raw_response.startswith("```json"):
        raw_response = raw_response[7:]  # Remove leading ```json
    if raw_response.endswith("```"):
        raw_response = raw_response[:-3]  # Remove trailing ```

    try:
        validation_output = json.loads(raw_response)  # Parse cleaned JSON
        
        # Ensure `score` exists; otherwise, return a default error response
        if "score" not in validation_output:
            print(f"❌ Missing 'score' key in response:\n{raw_response}")
            return {
                "title": title,
                "score": 0,  # Default fallback
                "status": "ERROR",
                "issues": ["Validation failed: No score returned"],
                "recommendations": {}
            }

    except json.JSONDecodeError as e:
        print(f"❌ JSON Parsing Error: {e}")
        print(f"⚠️ Raw Response:\n{raw_response}")
        return {
            "title": title,
            "score": 0,
            "status": "ERROR",
            "issues": ["JSON decoding error"],
            "recommendations": {},
            "raw_output": raw_response  # Save raw output for debugging
        }

    return validation_output 

# Loop Through Each Title & Process
for title in titles:
    print(f"🔄 Processing: {title}...")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)

    # Create a directory for the title
    title_folder = os.path.join(output_directory, safe_title)
    os.makedirs(title_folder, exist_ok=True)

    # Fetch top Google search results
    top_posts = get_top_google_results_scrapingbee(title)

    # Step 1: Scrape, Save, and Analyze Each Competitor Blog Separately
    seo_insights = []
    for idx, (post_title, post_url) in enumerate(top_posts[:3], start=1):
        print(f"🔍 Scraping Source {idx}: {post_url}")
        content = scrape_article(post_url)

        # Save raw scraped content
        competitor_filename = os.path.join(title_folder, f"{safe_title}_source{idx}.txt")
        with open(competitor_filename, "w", encoding="utf-8") as file:
            file.write(f"🔗 **Source {idx}:** {post_url}\n\n")
            file.write(content)

        # Analyze SEO of this competitor's blog separately
        seo_analysis = analyze_competitor_content(content)
        seo_insights.append(seo_analysis)

        # Save competitor SEO analysis
        seo_filename = os.path.join(title_folder, f"{safe_title}_source{idx}_seo_analysis.txt")
        with open(seo_filename, "w", encoding="utf-8") as file:
            file.write(seo_analysis)

    # Step 2: Combine Insights from All Analyzed Competitor Blogs
    combined_seo_analysis = "\n\n".join(seo_insights)

    # Save the combined SEO analysis
    combined_analysis_filename = os.path.join(title_folder, f"{safe_title}_seo_analysis_combined.txt")
    with open(combined_analysis_filename, "w", encoding="utf-8") as file:
        file.write(combined_seo_analysis)

    # Step 3: Generate Initial Blog Post Using the SEO Analysis
    blog_post = generate_blog_post(title, combined_seo_analysis)
    previous_blog_post = blog_post  # Store first version

    # Step 4: Validate the Blog (Iterate Until 100/100 Score)
    validation_result = validate_blog_post(title, blog_post)
    seo_score = validation_result["score"]
    validation_feedback = json.dumps(validation_result, indent=4)  # Convert JSON to formatted text

    while seo_score < 95:
        print(f"🚨 SEO Validation Failed for {title} (Score: {seo_score}/100). Rewriting with improvements...\n")

        # Save intermediate blog versions and validation feedback
        intermediate_blog_filename = os.path.join(title_folder, f"{safe_title}_SEO-{seo_score}.txt")
        validation_filename = os.path.join(title_folder, f"{safe_title}_SEO-{seo_score}_validation.txt")

        with open(intermediate_blog_filename, "w", encoding="utf-8") as file:
            file.write(f"**Title:** {title} (Score: {seo_score}/100)\n\n")
            file.write("📄 **Generated Blog Post:**\n")
            file.write(blog_post)

        with open(validation_filename, "w", encoding="utf-8") as file:
            file.write(f"**SEO Validation for:** {title} (Score: {seo_score}/100)\n\n")
            file.write(validation_feedback)  # Save JSON response as text

        # Print blog version and validation feedback
        print(f"\n📄 **Generated Blog (Score: {seo_score}/100)**:\n")
        print(blog_post)
        print(f"\n📝 **Validation Feedback:**\n{validation_feedback}\n")

        # Step 5: Generate an Improved Blog Based on Previous Version + Validation Feedback
        blog_post = generate_blog_post(title, combined_seo_analysis, previous_blog_post, validation_feedback)

        # Step 6: Validate Again
        validation_result = validate_blog_post(title, blog_post)
        seo_score = validation_result["score"]
        validation_feedback = json.dumps(validation_result, indent=4)

        # Store latest version for next iteration
        previous_blog_post = blog_post

    # Step 7: Save the Final Optimized Blog (Pass = 100/100)
    final_blog_filename = os.path.join(title_folder, f"{safe_title}_SEO-{seo_score}.txt")
    final_validation_filename = os.path.join(title_folder, f"{safe_title}_SEO-{seo_score}_validation.txt")

    with open(final_blog_filename, "w", encoding="utf-8") as file:
        file.write(f"**Title:** {title} (Final Score: {seo_score}/100)\n\n")
        file.write("📄 **Final Optimized Blog Post:**\n")
        file.write(blog_post)

    with open(final_validation_filename, "w", encoding="utf-8") as file:
        file.write(f"**Final SEO Validation for:** {title} (Score: {seo_score}/100)\n\n")
        file.write(validation_feedback)

    # Print final passed blog version
    print(f"\n✅ **Final Blog Version (Score: {seo_score}/100)**:\n")
    print(blog_post)
    print(f"\n📝 **Final Validation Feedback:**\n{validation_feedback}\n")
    print(f"\n🎉 Blog for '{title}' optimized to {seo_score}/100 and saved inside '{title_folder}'.\n")

print("\n🎯 All blog topics processed and stored in 'blog_data' folder!")

