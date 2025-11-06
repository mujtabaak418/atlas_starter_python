import os
from openai import OpenAI
from typing import Dict, Optional
import asyncio

client = None

def init_openai():
    """Initialize OpenAI client"""
    global client
    api_key = os.getenv('OPENAI_API_KEY', '')
    if api_key and api_key != 'sk-your-openai-key-here':
        client = OpenAI(api_key=api_key)
    return client is not None

async def process_resume_optimization(input_data: Dict) -> Dict:
    """Optimize a resume using AI"""
    resume_text = input_data.get('resume_text', '')
    target_job = input_data.get('target_job', 'general position')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    prompt = f"""You are an expert resume writer and career coach. Optimize the following resume for a {target_job} position.

ORIGINAL RESUME:
{resume_text}

Please provide:
1. An optimized version with improved formatting, stronger action verbs, and quantified achievements
2. A list of 5 key improvements made
3. ATS (Applicant Tracking System) optimization score (1-10)
4. 3 specific suggestions for further improvement

Format your response as JSON with keys: optimized_resume, improvements, ats_score, suggestions"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert resume optimization specialist. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content
        return {'result': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

async def process_cover_letter(input_data: Dict) -> Dict:
    """Generate a cover letter using AI"""
    resume_text = input_data.get('resume_text', '')
    job_description = input_data.get('job_description', '')
    company_name = input_data.get('company_name', 'the company')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    prompt = f"""Create a compelling cover letter for the following job application.

RESUME SUMMARY:
{resume_text[:1000]}

JOB DESCRIPTION:
{job_description}

COMPANY: {company_name}

Write a professional, engaging cover letter that:
1. Highlights relevant experience from the resume
2. Shows enthusiasm for the role
3. Demonstrates knowledge of the company
4. Is 3-4 paragraphs long
5. Uses a professional but warm tone"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert cover letter writer who creates compelling, personalized cover letters."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        return {'cover_letter': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

async def process_linkedin_optimization(input_data: Dict) -> Dict:
    """Optimize LinkedIn profile using AI"""
    current_profile = input_data.get('profile_text', '')
    industry = input_data.get('industry', 'professional')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    prompt = f"""Optimize this LinkedIn profile for maximum visibility and engagement in the {industry} industry.

CURRENT PROFILE:
{current_profile}

Provide:
1. Optimized headline (220 chars max)
2. Optimized about section (2600 chars max)
3. 5 keyword suggestions for SEO
4. 3 tips for profile improvement

Format as JSON with keys: headline, about, keywords, tips"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a LinkedIn optimization expert. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        result = response.choices[0].message.content
        return {'result': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

async def process_blog_post(input_data: Dict) -> Dict:
    """Generate SEO-optimized blog post"""
    topic = input_data.get('topic', '')
    keywords = input_data.get('keywords', [])
    word_count = input_data.get('word_count', 1000)
    tone = input_data.get('tone', 'professional')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    keywords_str = ', '.join(keywords) if keywords else 'relevant keywords'
    
    prompt = f"""Write a high-quality, SEO-optimized blog post about: {topic}

Requirements:
- Target word count: {word_count} words
- Tone: {tone}
- Include these keywords naturally: {keywords_str}
- Include H2 and H3 headings
- Add a compelling introduction and conclusion
- Make it engaging and valuable to readers
- Include actionable takeaways"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert content writer who creates engaging, SEO-optimized blog posts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2500
        )
        
        result = response.choices[0].message.content
        return {'blog_post': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

async def process_product_descriptions(input_data: Dict) -> Dict:
    """Generate product descriptions"""
    products = input_data.get('products', [])
    brand_voice = input_data.get('brand_voice', 'professional')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    descriptions = []
    total_tokens = 0
    
    for product in products[:10]:  # Limit to 10 products per batch
        prompt = f"""Write a compelling product description for:

Product Name: {product.get('name', 'Product')}
Features: {product.get('features', 'N/A')}
Target Audience: {product.get('target_audience', 'general consumers')}

Brand Voice: {brand_voice}

Create a 100-150 word description that:
1. Highlights key benefits
2. Uses persuasive language
3. Includes a call-to-action
4. Is SEO-friendly"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert copywriter specializing in product descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=300
            )
            
            descriptions.append({
                'product_name': product.get('name'),
                'description': response.choices[0].message.content
            })
            total_tokens += response.usage.total_tokens
        except Exception as e:
            descriptions.append({
                'product_name': product.get('name'),
                'error': str(e)
            })
    
    return {'descriptions': descriptions, 'tokens_used': total_tokens}

async def process_social_media_content(input_data: Dict) -> Dict:
    """Generate social media content package"""
    topic = input_data.get('topic', '')
    platforms = input_data.get('platforms', ['twitter', 'linkedin', 'facebook'])
    post_count = input_data.get('post_count', 5)
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    prompt = f"""Create {post_count} social media posts about: {topic}

Platforms: {', '.join(platforms)}

For each post, provide:
1. Platform-specific content (with appropriate length and style)
2. Relevant hashtags
3. Best posting time suggestion

Make posts engaging, shareable, and valuable. Format as JSON array."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a social media expert who creates viral, engaging content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=1500
        )
        
        result = response.choices[0].message.content
        return {'posts': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

async def process_business_name(input_data: Dict) -> Dict:
    """Generate business names and slogans"""
    industry = input_data.get('industry', '')
    description = input_data.get('description', '')
    style = input_data.get('style', 'modern')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    prompt = f"""Generate creative business names and slogans for:

Industry: {industry}
Description: {description}
Style: {style}

Provide:
1. 10 unique business name ideas
2. For each name, provide a catchy slogan
3. Brief explanation of the name's meaning
4. Domain availability suggestions (.com)

Format as JSON array with keys: name, slogan, meaning, domain"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative branding expert. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=1500
        )
        
        result = response.choices[0].message.content
        return {'result': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

async def process_email_template(input_data: Dict) -> Dict:
    """Generate email templates"""
    purpose = input_data.get('purpose', '')
    tone = input_data.get('tone', 'professional')
    audience = input_data.get('audience', 'general')
    
    if not client:
        return {'error': 'OpenAI API not configured'}
    
    prompt = f"""Create a professional email template for: {purpose}

Tone: {tone}
Audience: {audience}

Provide:
1. Subject line (with 2 alternatives)
2. Email body with [PLACEHOLDERS] for customization
3. Call-to-action
4. Professional signature template

Make it effective and easy to customize."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert email copywriter who creates high-converting email templates."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        result = response.choices[0].message.content
        return {'template': result, 'tokens_used': response.usage.total_tokens}
    except Exception as e:
        return {'error': str(e)}

# Service type to processor mapping
SERVICE_PROCESSORS = {
    'resume_optimization': process_resume_optimization,
    'cover_letter': process_cover_letter,
    'linkedin_optimization': process_linkedin_optimization,
    'blog_post': process_blog_post,
    'product_descriptions': process_product_descriptions,
    'social_media_content': process_social_media_content,
    'business_name': process_business_name,
    'email_template': process_email_template,
}

async def process_job(service_type: str, input_data: Dict) -> Dict:
    """Process a job based on service type"""
    processor = SERVICE_PROCESSORS.get(service_type)
    if not processor:
        return {'error': f'Unknown service type: {service_type}'}
    
    return await processor(input_data)
