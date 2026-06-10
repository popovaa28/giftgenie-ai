import os
import random
import json
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, session
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-genie-key-123")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

USER_DATABASE = {
    "testuser": "password123",
    "giftlover": "genie2026"
}

USER_SAVED_GIFTS = {}


@app.route('/')
def home():
    return render_template('index.html', username=session.get('username'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USER_DATABASE:
            return render_template('signup.html', error="That username already exists.")

        USER_DATABASE[username] = password
        USER_SAVED_GIFTS[username] = []
        session['username'] = username

        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USER_DATABASE and USER_DATABASE[username] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = session['username']
    saved_gifts = USER_SAVED_GIFTS.get(current_user, [])

    return render_template(
        'dashboard.html',
        username=current_user,
        saved_gifts=saved_gifts
    )


@app.route('/generate', methods=['POST'])
def generate():
    recipient_name = request.form.get('recipient_name')
    age = request.form.get('age')
    interest = request.form.get('interest')
    relation = request.form.get('relation')
    budget = request.form.get('budget')

    budget_number = int(budget)

    if budget_number <= 25:
        price_tier = "budget-friendly"
    elif budget_number <= 75:
        price_tier = "mid-range"
    else:
        price_tier = "premium"

    vibes = ["thoughtful", "creative", "cozy", "useful", "personalized", "unique"]
    selected_vibe = random.choice(vibes)

    system_instruction = (
        "You are GiftGenie. Return ONLY valid JSON. "
        "Do not use markdown, bullet points, or extra text."
    )

    user_prompt = (
        f"Suggest exactly 3 {selected_vibe}, {price_tier} gifts for {recipient_name}, "
        f"who is my {relation}. Age group: {age}. Interests: {interest}. "
        f"Budget: under ${budget}. Random seed: {random.random()}.\n\n"
        "Return the response as a JSON list. Each object must have exactly these keys: "
        "gift_name and why_it_works."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1.0
        )

        ai_message = response.choices[0].message.content
        gift_ideas = json.loads(ai_message)

        for gift in gift_ideas:
            search_terms = quote_plus(gift["gift_name"])
            gift["amazon_link"] = f"https://www.amazon.com/s?k={search_terms}"
            gift["etsy_link"] = f"https://www.etsy.com/search?q={search_terms}"
            gift["target_link"] = f"https://www.target.com/s?searchTerm={search_terms}"

        return render_template(
            'result.html',
            gift_ideas=gift_ideas,
            recipient_name=recipient_name,
            age=age,
            interest=interest,
            relation=relation,
            budget=budget,
            username=session.get('username')
        )

    except Exception as e:
        return f"Genie Error: {e}. Check your .env file!"


@app.route('/save_gift', methods=['POST'])
def save_gift():
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = session['username']

    saved_gift = {
        "recipient_name": request.form.get('recipient_name'),
        "relation": request.form.get('relation'),
        "age": request.form.get('age'),
        "interest": request.form.get('interest'),
        "budget": request.form.get('budget'),
        "gift_name": request.form.get('gift_name'),
        "why_it_works": request.form.get('why_it_works'),
        "amazon_link": request.form.get('amazon_link'),
        "etsy_link": request.form.get('etsy_link'),
        "target_link": request.form.get('target_link')
    }

    if current_user not in USER_SAVED_GIFTS:
        USER_SAVED_GIFTS[current_user] = []

    USER_SAVED_GIFTS[current_user].append(saved_gift)

    return redirect(url_for('dashboard'))


@app.route('/delete_gift/<int:gift_index>', methods=['POST'])
def delete_gift(gift_index):
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = session['username']

    if current_user in USER_SAVED_GIFTS:
        if 0 <= gift_index < len(USER_SAVED_GIFTS[current_user]):
            USER_SAVED_GIFTS[current_user].pop(gift_index)

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
