import os
import json
import logging
import requests
from flask import current_app
from app.services.analytics_service import (
    get_monthly_summary,
    get_category_expenses,
    get_budget_utilization,
    get_financial_health_score
)

logger = logging.getLogger(__name__)

def build_financial_context(user, month_str=None):
    """
    Assembles user's comprehensive financial profile into a clean dictionary
    for AI prompting or rule-based heuristics.
    """
    summary = get_monthly_summary(user.id, month_str)
    categories = get_category_expenses(user.id, month_str)
    utilization = get_budget_utilization(user.id, month_str)
    health = get_financial_health_score(user, month_str)
    currency = user.preferred_currency or 'INR'

    overspent = [item for item in utilization['items'] if item['percentage'] > 100.0]
    near_limit = [item for item in utilization['items'] if 90.0 <= item['percentage'] <= 100.0]

    return {
        'user_name': user.full_name,
        'currency': currency,
        'monthly_income': summary['monthly_income'],
        'monthly_expense': summary['monthly_expense'],
        'monthly_savings': summary['monthly_savings'],
        'savings_rate': summary['savings_rate'],
        'savings_target': user.monthly_savings_target or 0.0,
        'financial_goal': user.financial_goal or 'Financial Security',
        'health_score': health['score'],
        'health_rating': health['rating'],
        'top_categories': categories[:5],
        'overspent_categories': overspent,
        'near_limit_categories': near_limit,
        'total_budgeted': utilization['total_budgeted'],
        'budget_percentage': utilization['overall_percentage']
    }

def get_heuristic_recommendations(context):
    """
    Rule-based financial advisor engine that runs completely offline
    with zero API dependencies.
    """
    recs = []
    currency = context['currency']

    # 1. Income vs Expense Deficit
    if context['monthly_expense'] > context['monthly_income'] and context['monthly_income'] > 0:
        deficit = context['monthly_expense'] - context['monthly_income']
        recs.append({
            'type': 'danger',
            'icon': 'bi-exclamation-triangle-fill',
            'title': 'Deficit Alert: Spending Exceeds Income',
            'message': f"You have spent {currency} {deficit:,.2f} more than your recorded income this month. Immediately freeze non-essential expenses (Shopping, Dining, Entertainment) to prevent debt buildup."
        })
    elif context['monthly_income'] == 0:
        recs.append({
            'type': 'info',
            'icon': 'bi-wallet2',
            'title': 'Log Monthly Income',
            'message': "Add your monthly income streams to unlock full cashflow tracking, savings rate analysis, and automated budget limits."
        })

    # 2. Overspending Categories
    if context['overspent_categories']:
        over_names = ", ".join([f"{item['category']} ({item['percentage']}%)" for item in context['overspent_categories']])
        recs.append({
            'type': 'danger',
            'icon': 'bi-fire',
            'title': 'Overspending in Budgeted Categories',
            'message': f"The following categories have crossed your limit: {over_names}. Review recent transactions in these areas and look for recurring subscriptions or unneeded purchases."
        })

    # 3. Near Limit Warning
    if context['near_limit_categories']:
        warn_names = ", ".join([f"{item['category']} ({item['percentage']}%)" for item in context['near_limit_categories']])
        recs.append({
            'type': 'warning',
            'icon': 'bi-speedometer2',
            'title': 'Approaching Budget Limits',
            'message': f"You are within 10% of your allocated budget for: {warn_names}. Slow down discretionary purchases here for the rest of the month."
        })

    # 4. Savings Rate Assessment
    if context['monthly_income'] > 0:
        if context['savings_rate'] < 10.0:
            recs.append({
                'type': 'warning',
                'icon': 'bi-piggy-bank-fill',
                'title': 'Boost Your Savings Rate',
                'message': f"Your savings rate is currently {context['savings_rate']}%, which is below the recommended 20% benchmark. Aim to save at least {currency} {context['monthly_income'] * 0.20:,.2f} by adopting the 50/30/20 guideline."
            })
        elif context['savings_rate'] >= 25.0:
            recs.append({
                'type': 'success',
                'icon': 'bi-check-circle-fill',
                'title': 'Strong Savings Momentum',
                'message': f"Outstanding! You are saving {context['savings_rate']}% of your income. Consider routing surplus funds toward your goal: '{context['financial_goal']}' or low-cost index funds/emergency funds."
            })

    # 5. Top Expense Category Audit
    if context['top_categories']:
        top = context['top_categories'][0]
        if top['percentage'] >= 35.0:
            recs.append({
                'type': 'info',
                'icon': 'bi-pie-chart-fill',
                'title': f"Heavy Concentration in {top['category']}",
                'message': f"{top['category']} accounts for {top['percentage']}% of your total spending ({currency} {top['amount']:,.2f}). Check if any bills can be negotiated or bundled."
            })

    # 6. Default general wisdom if few transactions
    if not recs:
        recs.append({
            'type': 'primary',
            'icon': 'bi-lightbulb-fill',
            'title': 'Automate Your Savings First',
            'message': "Transfer your target savings amount immediately on payday before you start spending. This 'pay yourself first' habit guarantees financial resilience."
        })

    return recs

def call_gemini_api(prompt, api_key):
    """
    Calls Google Gemini API using REST endpoint.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=12)
    response.raise_for_status()
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text']

def call_openai_api(prompt, api_key, system_prompt="You are a professional financial advisor."):
    """
    Calls OpenAI Chat Completions API using REST endpoint.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 800
    }

    response = requests.post(url, headers=headers, json=payload, timeout=12)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']

def generate_ai_financial_recommendations(user, month_str=None):
    """
    Generates recommendations for user's dashboard and advisor page.
    Attempts live AI API if configured; falls back gracefully to heuristic engine.
    """
    context = build_financial_context(user, month_str)
    heuristic_recs = get_heuristic_recommendations(context)

    # Check for live AI provider
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    openai_key = current_app.config.get('OPENAI_API_KEY')
    provider = current_app.config.get('AI_PROVIDER', 'auto')

    ai_analysis_text = None

    prompt = f"""
You are an expert Personal Finance Advisor. Analyze the following user financial data for the month:
- User Name: {context['user_name']}
- Currency: {context['currency']}
- Monthly Income: {context['currency']} {context['monthly_income']}
- Monthly Expense: {context['currency']} {context['monthly_expense']}
- Monthly Savings: {context['currency']} {context['monthly_savings']} (Savings Rate: {context['savings_rate']}%)
- Monthly Savings Target: {context['currency']} {context['savings_target']}
- User's Goal: {context['financial_goal']}
- Financial Health Score: {context['health_score']}/100 ({context['health_rating']})
- Top Expense Categories: {json.dumps(context['top_categories'])}
- Overspent Categories: {json.dumps(context['overspent_categories'])}
- Near Limit Categories: {json.dumps(context['near_limit_categories'])}

Provide a concise, encouraging, and highly specific financial critique:
1. Identify any spending leaks or overspending.
2. Provide 3 actionable steps this month to improve savings and achieve their goal.
3. Suggest a realistic tweak to their budget allocation.
Keep the response formatted with clean markdown bullet points. Do not include generic fluff.
"""

    if (provider in ('gemini', 'auto')) and gemini_key:
        try:
            ai_analysis_text = call_gemini_api(prompt, gemini_key)
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}. Falling back.")

    if not ai_analysis_text and (provider in ('openai', 'auto')) and openai_key:
        try:
            ai_analysis_text = call_openai_api(prompt, openai_key)
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back.")

    # If no live AI response succeeded, build structured fallback commentary
    if not ai_analysis_text:
        ai_analysis_text = f"### Heuristic Financial Assessment for {context['user_name']}\n\n"
        ai_analysis_text += f"- **Current Cashflow Status**: You have earned {context['currency']} {context['monthly_income']:,.2f} and spent {context['currency']} {context['monthly_expense']:,.2f}, yielding a net savings of {context['currency']} {context['monthly_savings']:,.2f} ({context['savings_rate']}% savings rate).\n"
        
        if context['overspent_categories']:
            ai_analysis_text += f"- **Overspending Warning**: You have exceeded the allocated budget in {len(context['overspent_categories'])} category(ies). Focus on trimming unnecessary spending in these areas.\n"
        else:
            ai_analysis_text += "- **Budget Discipline**: Your spending is currently contained within your budgeted caps. Keep up this consistency.\n"
            
        ai_analysis_text += f"- **Goal Alignment**: To advance towards **'{context['financial_goal']}'**, aim to maintain an emergency buffer of at least 3-6 months worth of essential living expenses."

    return {
        'context': context,
        'recommendations': heuristic_recs,
        'ai_analysis': ai_analysis_text
    }

def generate_chat_response(user, user_message):
    """
    Responds to interactive chat messages in the Personal Finance Advisor Bot interface.
    """
    context = build_financial_context(user)
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    openai_key = current_app.config.get('OPENAI_API_KEY')
    provider = current_app.config.get('AI_PROVIDER', 'auto')

    prompt = f"""
You are 'FinBot', an empathetic, sharp, and highly practical AI Personal Finance Advisor.
The user is asking: "{user_message}"

Here is the user's current live financial snapshot:
- User: {context['user_name']}
- Currency: {context['currency']}
- Income: {context['currency']} {context['monthly_income']:,.2f}
- Expenses: {context['currency']} {context['monthly_expense']:,.2f}
- Net Savings: {context['currency']} {context['monthly_savings']:,.2f} (Savings Rate: {context['savings_rate']}%)
- Monthly Savings Target: {context['currency']} {context['savings_target']:,.2f}
- Primary Goal: {context['financial_goal']}
- Financial Health: {context['health_score']}/100 ({context['health_rating']})
- Overspent Categories: {[c['category'] for c in context['overspent_categories']]}
- Top Categories: {[f"{c['category']}: {context['currency']}{c['amount']}" for c in context['top_categories']]}

Answer the user directly, concisely (under 150 words), and reference their actual data whenever relevant.
"""

    if (provider in ('gemini', 'auto')) and gemini_key:
        try:
            return call_gemini_api(prompt, gemini_key)
        except Exception as e:
            logger.warning(f"Gemini chat failed: {e}")

    if (provider in ('openai', 'auto')) and openai_key:
        try:
            return call_openai_api(prompt, openai_key, system_prompt="You are FinBot, an intelligent personal finance coach.")
        except Exception as e:
            logger.warning(f"OpenAI chat failed: {e}")

    # Offline contextual heuristic chatbot logic
    q_lower = user_message.lower()
    curr = context['currency']

    if 'save' in q_lower or 'saving' in q_lower:
        return (
            f"Based on your current numbers, you have saved {curr} {context['monthly_savings']:,.2f} "
            f"this month, which is a {context['savings_rate']}% savings rate. "
            f"Your target is {curr} {context['savings_target']:,.2f}. "
            f"To boost savings, try automating transfers to a separate account right after receiving income, "
            f"and curtail discretionary spending in your highest category ({context['top_categories'][0]['category'] if context['top_categories'] else 'discretionary purchases'})."
        )
    elif 'budget' in q_lower or 'overspend' in q_lower or 'limit' in q_lower:
        if context['overspent_categories']:
            cats = ", ".join([c['category'] for c in context['overspent_categories']])
            return (
                f"You are currently over budget in: **{cats}**. "
                f"Your total spending is {curr} {context['monthly_expense']:,.2f}. "
                f"I recommend using our 'Auto-Generate Budget' tool on the Budget page to adopt the 50/30/20 rule and rebalance your limits."
            )
        else:
            return (
                f"Great news! None of your budget categories are overspent right now. "
                f"Your total monthly expenses stand at {curr} {context['monthly_expense']:,.2f}. "
                f"Keep an eye on nearing limits and maintain this steady discipline."
            )
    elif 'goal' in q_lower:
        return (
            f"Your active financial goal is: **'{context['financial_goal']}'**. "
            f"With your current net savings of {curr} {context['monthly_savings']:,.2f} this month, "
            f"you are making meaningful progress. You can manage and track specific milestones on the Goals page."
        )
    elif 'score' in q_lower or 'health' in q_lower:
        return (
            f"Your Financial Health Score is **{context['health_score']}/100 ({context['health_rating']})**. "
            f"This score reflects your savings rate ({context['savings_rate']}%), budget adherence, "
            f"and expense balance. Maintaining a savings rate above 20% will push your score into the Excellent range!"
        )
    else:
        return (
            f"Hello {context['user_name']}! You've recorded {curr} {context['monthly_income']:,.2f} in income and "
            f"{curr} {context['monthly_expense']:,.2f} in expenses this month, with a health score of {context['health_score']}/100. "
            f"Feel free to ask me about your savings rate, budget limits, how to cut spending, or how to reach your goal: '{context['financial_goal']}'."
        )
