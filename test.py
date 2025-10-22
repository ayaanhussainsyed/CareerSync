from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from functools import wraps
import certifi
import os
from openai import OpenAI
import re 
import base64 

app = Flask(__name__)
app.secret_key = '123'
client = MongoClient(
    "uri",
    tls=True,
    tlsCAFile=certifi.where()
)

db = client['NexusLMB']
users_collection = db['user_data']
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
     print("OPENAI_API_KEY environment variable not set. Using hardcoded key (less secure).")
     openai_api_key = "api"
openai_client = OpenAI(api_key=openai_api_key)

LEADERSHIP_SCENARIOS = {
    "Effective Communication": {
        "persona": "John, a junior employee who is struggling with performance and deadlines.",
        "context": "You are a team lead talking to John, a junior employee, about his poor performance and consistent delays. Your goal is to address the issue constructively, understand his challenges, and set clear expectations. Respond as John."
    },
    "Leadership": {
        "persona": "Sarah and David, two team members in conflict.",
        "context": "You are mediating a conflict between two team members, Sarah and David. Your goal is to understand both sides and find a resolution. Respond alternately as Sarah and David, or in a way that shows interaction between them."
    }
}

@app.route('/error', methods=['GET'])
def err():
    return render_template('error.html')

@app.route('/sign-up', methods=['GET', 'POST'])
def sign():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users_collection.find_one({'username': username}):
            flash('Username already exists. Try another one.')
            return redirect(url_for('sign'))
        users_collection.insert_one({'username': username, 'password': password})
        print("Account created")
        session['username'] = username

        return redirect(url_for('p1'))

    return render_template('sign-up.html')



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/tell-us-about-yourself', methods=["GET", "POST"])
@login_required 
def p1():
    if request.method == "POST":
        selected_dream = request.form.get('dream')
        final_dream = None
        if selected_dream:
            if selected_dream == "Other":
                final_dream = request.form.get('other-dream')
                if not final_dream:
                     flash("Please enter your dream in the 'Other' field.", "danger")
                     return redirect(url_for('p1'))
            else:
                final_dream = selected_dream
        else:
            flash("Please select a dream option.", "danger")
            return redirect(url_for('p1'))


        username = session.get('username')
        if username and final_dream is not None:
            user = users_collection.find_one({"username": username})
            if user:
                users_collection.update_one(
                    {"username": username},
                    {"$set": {"aim": final_dream}}
                )
                flash("Your preferences have been saved!", "success")
                return redirect(url_for('login'))
            else:
                flash("User not found. Please log in first.", "danger")
                return redirect(url_for('login'))
        else:
            flash("Could not save preference. Please try logging in again.", "danger")
            return redirect(url_for('login'))

    return render_template("p1.html")


@app.route('/', methods=['GET','POST'])
def login():
    if request.method=="POST":
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({'username': username})
        if user and user['password'] == password:
            session['username'] = username
            session['leadership_chat_history'] = []
            return redirect(url_for('main'))
        else:
            return redirect(url_for("err"))
    return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    session.pop('leadership_chat_history', None) 
    return redirect(url_for('login'))


@app.route('/main')
@login_required
def main():
    return render_template('main.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route('/dna-mapping')
@login_required
def dna():
    ai_response = session.pop('ai_response', None)
    suggested_career = session.pop('suggested_career', None) 
    return render_template('dnamap.html', ai_response=ai_response, suggested_career=suggested_career)


@app.route('/analyse-dna', methods=['POST'])
@login_required
def analyse_dna():
    if request.method == 'POST':
        stream = request.form.get('stream')
        interests = request.form.get('interests')
        creativity = request.form.get('creativity')
        logic = request.form.get('logic')
        communication = request.form.get('communication')
        leadership = request.form.get('leadership')
        curiosity = request.form.get('curiosity')
        prompt_text = f"""As a career counselor, analyze the following user inputs and provide career recommendations and insights based on their Stream, Interests, and self-rated skills.

User Inputs:
Stream: {stream}
Interests: {interests}
Creativity (out of 10): {creativity}
Logic (out of 10): {logic}
Communication (out of 10): {communication}
Leadership (out of 10): {leadership}
Curiosity (out of 10): {curiosity}

Please provide a detailed analysis and suggest potential career paths that align with these factors. **Start your response by clearly stating the primary recommended career and enclose it EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER]**. For example: "Based on your profile, your primary recommended career is [CAREERSYNC_CAREER]Software Engineer[/CAREERSYNC_CAREER]. This role typically involves..." Provide the response in a clear, well-formatted manner, suitable for display.
"""
        system_message = """You are a helpful career counselor analyzing user profiles. Provide a response which is elaborate and interactive and fun, results should NOT BE DRY.
        Include the primary recommended career enclosed EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER] within your response as instructed by the user prompt.
        """

        try:
            response = openai_client.chat.completions.create(
                model="ft:gpt-4.1-mini-2025-04-14:personal:careersync:BUW1r4fH", 
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_text}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            model_response_text = response.choices[0].message.content
            career_match = re.search(r'\[CAREERSYNC_CAREER\](.*?)\[/CAREERSYNC_CAREER\]', model_response_text, re.DOTALL)

            suggested_career = None
            if career_match:
                suggested_career = career_match.group(1).strip()
                model_response_for_display = re.sub(r'\[CAREERSYNC_CAREER\].*?\[/CAREERSYNC_CAREER\]', suggested_career, model_response_text, flags=re.DOTALL)
            else:
                print("Warning: CAREERSYNC_CAREER tags not found in LLM response. Client-side heuristic may be used.")
                model_response_for_display = model_response_text 
            session['ai_response'] = model_response_for_display
            session['suggested_career'] = suggested_career 
            print(f"Backend Extracted Career: {suggested_career}")
            return redirect(url_for('dna'))

        except Exception as e:
            print(f"Error calling OpenAI API for DNA Mapping: {e}")
            session['ai_response'] = f"An error occurred during analysis: {e}"
            session['suggested_career'] = None # Ensure no career is passed on error
            return redirect(url_for('dna'))


@app.route('/future-you')
@login_required
def future():
    envision_response = session.pop('envision_response', None)
    return render_template("future_you.html", envision_response=envision_response)


@app.route('/envision-career', methods=['POST'])
@login_required
def envision_career():
    if request.method == 'POST':
        chosen_career = request.form.get('career')

        if not chosen_career or chosen_career.lower() == 'career not found': # Added check for fallback text
             flash("Could not determine the career to envision. Please perform the DNA mapping again.", "warning")
             return redirect(url_for('future'))

        prompt_text = f"""As a career guidance AI, provide a detailed vision for a user envisioning themselves in the career of a "{chosen_career}".

Describe the following aspects:
1.  **A Typical Day in the Life:** What would a typical day look like for someone in this role?
2.  **Annual Pay:** Provide a realistic range for annual salary. Mention factors that influence pay (experience, location, industry). Include an estimate of inflation-adjusted salary for the next few years (2026, 2027, 2028), clearly stating assumptions or that these are estimates.
3.  **Best Countries:** List some of the top countries globally to pursue this career, considering job opportunities, industry strength, and quality of life.
4.  **Relevant Colleges/Courses:** Suggest types of degrees, specific courses, or top universities/institutions that would be beneficial for pursuing this career.

Format the response clearly using Markdown. Use headings (##), bold text (**), and lists (-) where appropriate. Ensure the response is well-structured and easy to read with clear sections.
"""
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant providing career envisioning details. Format your response using Markdown, including headings (##), bold text (**), and lists (-) for clarity. Provide the inflation-adjusted salary estimates as requested, clearly stating they are estimates based on current trends."},
                    {"role": "user", "content": prompt_text}
                ],
                max_tokens=1800,
                temperature=0.7
            )

            model_response = response.choices[0].message.content
            session['envision_response'] = model_response

            print("\n--- Future You AI Response ---")
            print(f"Envisioning career: {chosen_career}")
            print(model_response)
            print("------------------------------\n")
            return redirect(url_for('future'))

        except Exception as e:
            print(f"Error calling OpenAI API for Future You: {e}")
            flash(f"An error occurred while envisioning your future: {e}", "danger")
            session['envision_response'] = f"Error: Could not generate envisioned future. {e}"
            return redirect(url_for('future'))




@app.route('/leadership-lab')
@login_required
def leader():
     session['leadership_chat_history'] = []
     return render_template("leadership.html")

@app.route('/send-leadership-prompt', methods=['POST'])
@login_required
def send_leadership_prompt():
    data = request.json
    user_message = data.get('user_message')
    skill = data.get('skill')
    if not user_message or not skill:
        return jsonify({"error": "Missing user message or skill"}), 400

    scenario = LEADERSHIP_SCENARIOS.get(skill)
    if not scenario:
        return jsonify({"error": "Invalid skill selected"}), 400

    chat_history = session.get('leadership_chat_history', [])
    chat_history.append({"role": "user", "content": user_message})
    system_message = f"""You are an AI role-playing assistant for practicing "{skill}" skills.
Your role is to act as "{scenario['persona']}" in the following scenario:
{scenario['context']}

Before each response as the persona, you MUST provide a rating out of 10 for the user's *previous* message based on their application of "{skill}" principles in this scenario. Format the rating clearly in bold brackets, e.g., **[Rating: X/10]**.
After the rating (just a rating out of 10, you are not supposed to elaborate on the rating just continue with your response), provide your response in character (You will either be Sarah or John in either of the cases but you wont refer to yourself as David or anyone else), continuing the role-play.
Keep responses concise but realistic for the role-play.
"""

    messages = [{"role": "system", "content": system_message}]
    messages.extend(chat_history)


    print("\n--- OpenAI Prompt ---")
    print(f"System: {system_message}")
    for msg in messages:
         print(f"{msg['role']}: {msg['content']}")
    print("---------------------\n")


    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1", 
            messages=messages,
            max_tokens=300, 
            temperature=0.8 
        )

        ai_response_content = response.choices[0].message.content.strip()

        print("\n--- Raw AI Response ---")
        print(ai_response_content)
        print("-----------------------\n")
        chat_history.append({"role": "assistant", "content": ai_response_content})
        session['leadership_chat_history'] = chat_history 
        return jsonify({"ai_response": ai_response_content, "updated_history": chat_history}) 

    except Exception as e:
        print(f"Error calling OpenAI API for Leadership Lab: {e}")
        error_message = f"An error occurred: {e}"
        chat_history.append({"role": "assistant", "content": f"[Error] {error_message}"})
        session['leadership_chat_history'] = chat_history 
        return jsonify({"error": error_message, "ai_response": f"[Error] {error_message}", "updated_history": chat_history}), 500

@app.route('/end-leadership-scenario', methods=['POST'])
@login_required
def end_leadership_scenario():
    data = request.json
    skill = data.get('skill')
    chat_history = data.get('history', [])

    if not skill or not chat_history:
        return jsonify({"error": "Missing skill or chat history"}), 400

    scenario = LEADERSHIP_SCENARIOS.get(skill)
    if not scenario:
        return jsonify({"error": "Invalid skill provided"}), 400
    feedback_prompt = f"""You have completed a role-playing scenario for "{skill}" practice.
Based on the following conversation history in which you played the role of "{scenario['persona']}", evaluate the user's performance as the leader/team lead.

Provide your feedback in a clear, well-formatted manner, suitable for display in a popup.
Include:
1. An overall rating out of 10 for the user's performance throughout the scenario.
2. Specific feedback on their strengths demonstrated during the conversation.
3. Concrete, actionable tips for improvement for future scenarios or real-life situations.

Structure your response using Markdown, with clear headings for each section (Overall Rating, Strengths, Tips for Improvement).

Conversation History:
"""

    history_text = "\n".join([f"{turn['role'].capitalize()}: {turn['content']}" for turn in chat_history])
    final_prompt = feedback_prompt + history_text
    messages = [
         {"role": "system", "content": "You are an AI providing constructive feedback on a user's leadership/communication practice scenario. Provide a clear, well-structured evaluation in Markdown."},
         {"role": "user", "content": final_prompt}
    ]

    print("\n--- Feedback Prompt ---")
    print(f"System: You are an AI providing constructive feedback...")
    print(f"User: {final_prompt[:500]}...") 
    print("---------------------------\n")


    try:
        response = openai_client.chat.completions.create(
             model="gpt-4.1",
             messages=messages,
             max_tokens=500, 
             temperature=0.7 
        )

        feedback_content = response.choices[0].message.content.strip()

        print("\n--- Raw Feedback Response ---")
        print(feedback_content)
        print("---------------------------\n")
        session.pop('leadership_chat_history', None)

        return jsonify({"feedback": feedback_content})

    except Exception as e:
        print(f"Error generating feedback: {e}")
        # Still clear history even on error
        session.pop('leadership_chat_history', None)
        return jsonify({"error": f"Could not generate feedback: {e}", "feedback": f"An error occurred while generating feedback: {e}"}), 500


@app.route('/gradescope')
@login_required
def gradescope():
     return render_template("gradescope.html")

@app.route('/upload-reportcard', methods=['POST'])
@login_required
def upload_reportcard():
    if 'report_card' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['report_card']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        try:
            image_bytes = file.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            prompt_text = """Analyze the provided report card image. Based on the subjects and grades visible, recommend a suitable academic stream (Science, Commerce, or Arts) for the student. Provide a short, elaborate reason for your recommendation, highlighting strengths indicated by the grades.

            Output format:
            Recommended Stream: [Stream Name]
            Reason: [Short, elaborate reason based on grades]
            """

            response = openai_client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": "You are an AI career advisor specializing in academic stream recommendations based on report cards."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}} # Assuming JPEG format, adjust if needed
                    ]}
                ],
                max_tokens=300, 
                temperature=0.5
            )

            analysis_result = response.choices[0].message.content.strip()

            print("\n--- Report Card Analysis Result ---")
            print(analysis_result)
            print("-----------------------------------\n")
            session['last_report_card_analysis'] = analysis_result

            return jsonify({"analysis": analysis_result})

        except Exception as e:
            print(f"Error processing report card: {e}")
            return jsonify({"error": f"Failed to analyze report card: {e}"}), 500

    return jsonify({"error": "Something went wrong with the file upload."}), 500

# New route to handle follow-up questions
@app.route('/ask-followup', methods=['POST'])
@login_required
def ask_followup():
    data = request.json
    question = data.get('question')
    analysis_context = data.get('analysis_context') # Get the previous analysis from the frontend

    if not question:
        return jsonify({"error": "No question provided"}), 400

    if not analysis_context:
         return jsonify({"error": "No previous analysis context found. Please upload a report card first."}), 400


    try:
        # Construct the prompt with the previous analysis as context
        prompt_text = f"""Based on the previous report card analysis:
{analysis_context}

The user has a follow-up question: "{question}"

Please answer the user's follow-up question, referencing the report card analysis provided. Keep the answer concise and relevant.
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI career advisor answering follow-up questions based on a previous report card analysis."},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=200, 
            temperature=0.7
        )

        followup_answer = response.choices[0].message.content.strip()

        print("\n--- Follow-up Question Answer ---")
        print(followup_answer)
        print("---------------------------------\n")


        return jsonify({"answer": followup_answer})

    except Exception as e:
        print(f"Error processing follow-up question: {e}")
        return jsonify({"error": f"Failed to answer follow-up question: {e}"}), 500


if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')

    app.run(debug=True, port=7479)




# from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# from pymongo import MongoClient
# from functools import wraps
# import certifi
# import os
# from openai import OpenAI
# import re 
# import base64 

# app = Flask(__name__)
# app.secret_key = '123'
# client = MongoClient(
#     "uri",
#     tls=True,
#     tlsCAFile=certifi.where()
# )

# db = client['NexusLMB']
# users_collection = db['user_data']
# openai_api_key = os.environ.get("OPENAI_API_KEY")
# if not openai_api_key:
#      print("OPENAI_API_KEY environment variable not set. Using hardcoded key (less secure).")
#      openai_api_key = "api"
# openai_client = OpenAI(api_key=openai_api_key)

# LEADERSHIP_SCENARIOS = {
#     "Effective Communication": {
#         "persona": "John, a junior employee who is struggling with performance and deadlines.",
#         "context": "You are a team lead talking to John, a junior employee, about his poor performance and consistent delays. Your goal is to address the issue constructively, understand his challenges, and set clear expectations. Respond as John."
#     },
#     "Leadership": {
#         "persona": "Sarah and David, two team members in conflict.",
#         "context": "You are mediating a conflict between two team members, Sarah and David. Your goal is to understand both sides and find a resolution. Respond alternately as Sarah and David, or in a way that shows interaction between them."
#     }
# }

# @app.route('/error', methods=['GET'])
# def err():
#     return render_template('error.html')

# @app.route('/sign-up', methods=['GET', 'POST'])
# def sign():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if users_collection.find_one({'username': username}):
#             flash('Username already exists. Try another one.')
#             return redirect(url_for('sign'))
#         users_collection.insert_one({'username': username, 'password': password})
#         print("Account created")
#         session['username'] = username

#         return redirect(url_for('p1'))

#     return render_template('sign-up.html')



# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'username' not in session:
#             flash("Please log in to access this page.")
#             return redirect(url_for('login'))
#         return f(*args, **kwargs)
#     return decorated_function

# @app.route('/tell-us-about-yourself', methods=["GET", "POST"])
# @login_required 
# def p1():
#     if request.method == "POST":
#         selected_dream = request.form.get('dream')
#         final_dream = None
#         if selected_dream:
#             if selected_dream == "Other":
#                 final_dream = request.form.get('other-dream')
#                 if not final_dream:
#                      flash("Please enter your dream in the 'Other' field.", "danger")
#                      return redirect(url_for('p1'))
#             else:
#                 final_dream = selected_dream
#         else:
#             flash("Please select a dream option.", "danger")
#             return redirect(url_for('p1'))


#         username = session.get('username')
#         if username and final_dream is not None:
#             user = users_collection.find_one({"username": username})
#             if user:
#                 users_collection.update_one(
#                     {"username": username},
#                     {"$set": {"aim": final_dream}}
#                 )
#                 flash("Your preferences have been saved!", "success")
#                 return redirect(url_for('login'))
#             else:
#                 flash("User not found. Please log in first.", "danger")
#                 return redirect(url_for('login'))
#         else:
#             flash("Could not save preference. Please try logging in again.", "danger")
#             return redirect(url_for('login'))

#     return render_template("p1.html")


# @app.route('/', methods=['GET','POST'])
# def login():
#     if request.method=="POST":
#         username = request.form['username']
#         password = request.form['password']
#         user = users_collection.find_one({'username': username})
#         if user and user['password'] == password:
#             session['username'] = username
#             session['leadership_chat_history'] = []
#             return redirect(url_for('main'))
#         else:
#             return redirect(url_for("err"))
#     return render_template("login.html")


# @app.route('/logout')
# @login_required
# def logout():
#     session.pop('username', None)
#     session.pop('leadership_chat_history', None) 
#     return redirect(url_for('login'))


# @app.route('/main')
# @login_required
# def main():
#     return render_template('main.html')


# @app.route('/dashboard')
# @login_required
# def dashboard():
#     return render_template("dashboard.html")


# @app.route('/dna-mapping')
# @login_required
# def dna():
#     ai_response = session.pop('ai_response', None)
#     suggested_career = session.pop('suggested_career', None) 
#     return render_template('dnamap.html', ai_response=ai_response, suggested_career=suggested_career)


# @app.route('/analyse-dna', methods=['POST'])
# @login_required
# def analyse_dna():
#     if request.method == 'POST':
#         stream = request.form.get('stream')
#         interests = request.form.get('interests')
#         creativity = request.form.get('creativity')
#         logic = request.form.get('logic')
#         communication = request.form.get('communication')
#         leadership = request.form.get('leadership')
#         curiosity = request.form.get('curiosity')
#         prompt_text = f"""As a career counselor, analyze the following user inputs and provide career recommendations and insights based on their Stream, Interests, and self-rated skills.

# User Inputs:
# Stream: {stream}
# Interests: {interests}
# Creativity (out of 10): {creativity}
# Logic (out of 10): {logic}
# Communication (out of 10): {communication}
# Leadership (out of 10): {leadership}
# Curiosity (out of 10): {curiosity}

# Please provide a detailed analysis and suggest potential career paths that align with these factors. **Start your response by clearly stating the primary recommended career and enclose it EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER]**. For example: "Based on your profile, your primary recommended career is [CAREERSYNC_CAREER]Software Engineer[/CAREERSYNC_CAREER]. This role typically involves..." Provide the response in a clear, well-formatted manner, suitable for display.
# """
#         system_message = """You are a helpful career counselor analyzing user profiles. Provide a response which is elaborate and interactive and fun, results should NOT BE DRY.
#         Include the primary recommended career enclosed EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER] within your response as instructed by the user prompt.
#         """

#         try:
#             response = openai_client.chat.completions.create(
#                 model="ft:gpt-4.1-mini-2025-04-14:personal:careersync:BUW1r4fH", 
#                 messages=[
#                     {"role": "system", "content": system_message},
#                     {"role": "user", "content": prompt_text}
#                 ],
#                 max_tokens=1000,
#                 temperature=0.7
#             )

#             model_response_text = response.choices[0].message.content
#             career_match = re.search(r'\[CAREERSYNC_CAREER\](.*?)\[/CAREERSYNC_CAREER\]', model_response_text, re.DOTALL)

#             suggested_career = None
#             if career_match:
#                 suggested_career = career_match.group(1).strip()
#                 model_response_for_display = re.sub(r'\[CAREERSYNC_CAREER\].*?\[/CAREERSYNC_CAREER\]', suggested_career, model_response_text, flags=re.DOTALL)
#             else:
#                 print("Warning: CAREERSYNC_CAREER tags not found in LLM response. Client-side heuristic may be used.")
#                 model_response_for_display = model_response_text 
#             session['ai_response'] = model_response_for_display
#             session['suggested_career'] = suggested_career 
#             print(f"Backend Extracted Career: {suggested_career}")
#             return redirect(url_for('dna'))

#         except Exception as e:
#             print(f"Error calling OpenAI API for DNA Mapping: {e}")
#             session['ai_response'] = f"An error occurred during analysis: {e}"
#             session['suggested_career'] = None # Ensure no career is passed on error
#             return redirect(url_for('dna'))


# @app.route('/future-you')
# @login_required
# def future():
#     envision_response = session.pop('envision_response', None)
#     return render_template("future_you.html", envision_response=envision_response)


# @app.route('/envision-career', methods=['POST'])
# @login_required
# def envision_career():
#     if request.method == 'POST':
#         chosen_career = request.form.get('career')

#         if not chosen_career or chosen_career.lower() == 'career not found': # Added check for fallback text
#              flash("Could not determine the career to envision. Please perform the DNA mapping again.", "warning")
#              return redirect(url_for('future'))

#         prompt_text = f"""As a career guidance AI, provide a detailed vision for a user envisioning themselves in the career of a "{chosen_career}".

# Describe the following aspects:
# 1.  **A Typical Day in the Life:** What would a typical day look like for someone in this role?
# 2.  **Annual Pay:** Provide a realistic range for annual salary. Mention factors that influence pay (experience, location, industry). Include an estimate of inflation-adjusted salary for the next few years (2026, 2027, 2028), clearly stating assumptions or that these are estimates.
# 3.  **Best Countries:** List some of the top countries globally to pursue this career, considering job opportunities, industry strength, and quality of life.
# 4.  **Relevant Colleges/Courses:** Suggest types of degrees, specific courses, or top universities/institutions that would be beneficial for pursuing this career.

# Format the response clearly using Markdown. Use headings (##), bold text (**), and lists (-) where appropriate. Ensure the response is well-structured and easy to read with clear sections.
# """
#         try:
#             response = openai_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are a helpful AI assistant providing career envisioning details. Format your response using Markdown, including headings (##), bold text (**), and lists (-) for clarity. Provide the inflation-adjusted salary estimates as requested, clearly stating they are estimates based on current trends."},
#                     {"role": "user", "content": prompt_text}
#                 ],
#                 max_tokens=1800,
#                 temperature=0.7
#             )

#             model_response = response.choices[0].message.content
#             session['envision_response'] = model_response

#             print("\n--- Future You AI Response ---")
#             print(f"Envisioning career: {chosen_career}")
#             print(model_response)
#             print("------------------------------\n")
#             return redirect(url_for('future'))

#         except Exception as e:
#             print(f"Error calling OpenAI API for Future You: {e}")
#             flash(f"An error occurred while envisioning your future: {e}", "danger")
#             session['envision_response'] = f"Error: Could not generate envisioned future. {e}"
#             return redirect(url_for('future'))




# @app.route('/leadership-lab')
# @login_required
# def leader():
#      session['leadership_chat_history'] = []
#      return render_template("leadership.html")

# @app.route('/send-leadership-prompt', methods=['POST'])
# @login_required
# def send_leadership_prompt():
#     data = request.json
#     user_message = data.get('user_message')
#     skill = data.get('skill')
#     if not user_message or not skill:
#         return jsonify({"error": "Missing user message or skill"}), 400

#     scenario = LEADERSHIP_SCENARIOS.get(skill)
#     if not scenario:
#         return jsonify({"error": "Invalid skill selected"}), 400

#     chat_history = session.get('leadership_chat_history', [])
#     chat_history.append({"role": "user", "content": user_message})
#     system_message = f"""You are an AI role-playing assistant for practicing "{skill}" skills.
# Your role is to act as "{scenario['persona']}" in the following scenario:
# {scenario['context']}

# Before each response as the persona, you MUST provide a rating out of 10 for the user's *previous* message based on their application of "{skill}" principles in this scenario. Format the rating clearly in bold brackets, e.g., **[Rating: X/10]**.
# After the rating (just a rating out of 10, you are not supposed to elaborate on the rating just continue with your response), provide your response in character (You will either be Sarah or John in either of the cases but you wont refer to yourself as David or anyone else), continuing the role-play.
# Keep responses concise but realistic for the role-play.
# """

#     messages = [{"role": "system", "content": system_message}]
#     messages.extend(chat_history)


#     print("\n--- OpenAI Prompt ---")
#     print(f"System: {system_message}")
#     for msg in messages:
#          print(f"{msg['role']}: {msg['content']}")
#     print("---------------------\n")


#     try:
#         response = openai_client.chat.completions.create(
#             model="gpt-4.1", 
#             messages=messages,
#             max_tokens=300, 
#             temperature=0.8 
#         )

#         ai_response_content = response.choices[0].message.content.strip()

#         print("\n--- Raw AI Response ---")
#         print(ai_response_content)
#         print("-----------------------\n")
#         chat_history.append({"role": "assistant", "content": ai_response_content})
#         session['leadership_chat_history'] = chat_history 
#         return jsonify({"ai_response": ai_response_content, "updated_history": chat_history}) 

#     except Exception as e:
#         print(f"Error calling OpenAI API for Leadership Lab: {e}")
#         error_message = f"An error occurred: {e}"
#         chat_history.append({"role": "assistant", "content": f"[Error] {error_message}"})
#         session['leadership_chat_history'] = chat_history 
#         return jsonify({"error": error_message, "ai_response": f"[Error] {error_message}", "updated_history": chat_history}), 500

# @app.route('/end-leadership-scenario', methods=['POST'])
# @login_required
# def end_leadership_scenario():
#     data = request.json
#     skill = data.get('skill')
#     chat_history = data.get('history', [])

#     if not skill or not chat_history:
#         return jsonify({"error": "Missing skill or chat history"}), 400

#     scenario = LEADERSHIP_SCENARIOS.get(skill)
#     if not scenario:
#         return jsonify({"error": "Invalid skill provided"}), 400
#     feedback_prompt = f"""You have completed a role-playing scenario for "{skill}" practice.
# Based on the following conversation history in which you played the role of "{scenario['persona']}", evaluate the user's performance as the leader/team lead.

# Provide your feedback in a clear, well-formatted manner, suitable for display in a popup.
# Include:
# 1. An overall rating out of 10 for the user's performance throughout the scenario.
# 2. Specific feedback on their strengths demonstrated during the conversation.
# 3. Concrete, actionable tips for improvement for future scenarios or real-life situations.

# Structure your response using Markdown, with clear headings for each section (Overall Rating, Strengths, Tips for Improvement).

# Conversation History:
# """

#     history_text = "\n".join([f"{turn['role'].capitalize()}: {turn['content']}" for turn in chat_history])
#     final_prompt = feedback_prompt + history_text
#     messages = [
#          {"role": "system", "content": "You are an AI providing constructive feedback on a user's leadership/communication practice scenario. Provide a clear, well-structured evaluation in Markdown."},
#          {"role": "user", "content": final_prompt}
#     ]

#     print("\n--- Feedback Prompt ---")
#     print(f"System: You are an AI providing constructive feedback...")
#     print(f"User: {final_prompt[:500]}...") 
#     print("---------------------------\n")


#     try:
#         response = openai_client.chat.completions.create(
#              model="gpt-4.1",
#              messages=messages,
#              max_tokens=500, 
#              temperature=0.7 
#         )

#         feedback_content = response.choices[0].message.content.strip()

#         print("\n--- Raw Feedback Response ---")
#         print(feedback_content)
#         print("---------------------------\n")
#         session.pop('leadership_chat_history', None)

#         return jsonify({"feedback": feedback_content})

#     except Exception as e:
#         print(f"Error generating feedback: {e}")
#         # Still clear history even on error
#         session.pop('leadership_chat_history', None)
#         return jsonify({"error": f"Could not generate feedback: {e}", "feedback": f"An error occurred while generating feedback: {e}"}), 500


# @app.route('/gradescope')
# @login_required
# def gradescope():
#      return render_template("gradescope.html")

# @app.route('/upload-reportcard', methods=['POST'])
# @login_required
# def upload_reportcard():
#     if 'report_card' not in request.files:
#         return jsonify({"error": "No file part in the request"}), 400

#     file = request.files['report_card']

#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400

#     if file:
#         try:
#             image_bytes = file.read()
#             base64_image = base64.b64encode(image_bytes).decode('utf-8')
#             prompt_text = """Analyze the provided report card image. Based on the subjects and grades visible, recommend a suitable academic stream (Science, Commerce, or Arts) for the student. Provide a short, elaborate reason for your recommendation, highlighting strengths indicated by the grades.

#             Output format:
#             Recommended Stream: [Stream Name]
#             Reason: [Short, elaborate reason based on grades]
#             """

#             response = openai_client.chat.completions.create(
#                 model="gpt-4o", 
#                 messages=[
#                     {"role": "system", "content": "You are an AI career advisor specializing in academic stream recommendations based on report cards."},
#                     {"role": "user", "content": [
#                         {"type": "text", "text": prompt_text},
#                         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}} # Assuming JPEG format, adjust if needed
#                     ]}
#                 ],
#                 max_tokens=300, 
#                 temperature=0.5
#             )

#             analysis_result = response.choices[0].message.content.strip()

#             print("\n--- Report Card Analysis Result ---")
#             print(analysis_result)
#             print("-----------------------------------\n")
#             session['last_report_card_analysis'] = analysis_result

#             return jsonify({"analysis": analysis_result})

#         except Exception as e:
#             print(f"Error processing report card: {e}")
#             return jsonify({"error": f"Failed to analyze report card: {e}"}), 500

#     return jsonify({"error": "Something went wrong with the file upload."}), 500

# # New route to handle follow-up questions
# @app.route('/ask-followup', methods=['POST'])
# @login_required
# def ask_followup():
#     data = request.json
#     question = data.get('question')
#     analysis_context = data.get('analysis_context') # Get the previous analysis from the frontend

#     if not question:
#         return jsonify({"error": "No question provided"}), 400

#     if not analysis_context:
#          return jsonify({"error": "No previous analysis context found. Please upload a report card first."}), 400


#     try:
#         # Construct the prompt with the previous analysis as context
#         prompt_text = f"""Based on the previous report card analysis:
# {analysis_context}

# The user has a follow-up question: "{question}"

# Please answer the user's follow-up question, referencing the report card analysis provided. Keep the answer concise and relevant.
# """

#         response = openai_client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are an AI career advisor answering follow-up questions based on a previous report card analysis."},
#                 {"role": "user", "content": prompt_text}
#             ],
#             max_tokens=200, 
#             temperature=0.7
#         )

#         followup_answer = response.choices[0].message.content.strip()

#         print("\n--- Follow-up Question Answer ---")
#         print(followup_answer)
#         print("---------------------------------\n")


#         return jsonify({"answer": followup_answer})

#     except Exception as e:
#         print(f"Error processing follow-up question: {e}")
#         return jsonify({"error": f"Failed to answer follow-up question: {e}"}), 500


# if __name__ == '__main__':
#     if not os.path.exists('templates'):
#         os.makedirs('templates')

#     app.run(debug=True, port=7479)




# from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# from pymongo import MongoClient
# from functools import wraps
# import certifi
# import os
# from openai import OpenAI
# import re 
# import base64 

# app = Flask(__name__)
# app.secret_key = '123'
# client = MongoClient(
#     "uri",
#     tls=True,
#     tlsCAFile=certifi.where()
# )

# db = client['NexusLMB']
# users_collection = db['user_data']
# openai_api_key = os.environ.get("OPENAI_API_KEY")
# if not openai_api_key:
#      print("OPENAI_API_KEY environment variable not set. Using hardcoded key (less secure).")
#      openai_api_key = "api"
# openai_client = OpenAI(api_key=openai_api_key)

# LEADERSHIP_SCENARIOS = {
#     "Effective Communication": {
#         "persona": "John, a junior employee who is struggling with performance and deadlines.",
#         "context": "You are a team lead talking to John, a junior employee, about his poor performance and consistent delays. Your goal is to address the issue constructively, understand his challenges, and set clear expectations. Respond as John."
#     },
#     "Leadership": {
#         "persona": "Sarah and David, two team members in conflict.",
#         "context": "You are mediating a conflict between two team members, Sarah and David. Your goal is to understand both sides and find a resolution. Respond alternately as Sarah and David, or in a way that shows interaction between them."
#     }
# }

# @app.route('/error', methods=['GET'])
# def err():
#     return render_template('error.html')

# @app.route('/sign-up', methods=['GET', 'POST'])
# def sign():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if users_collection.find_one({'username': username}):
#             flash('Username already exists. Try another one.')
#             return redirect(url_for('sign'))
#         users_collection.insert_one({'username': username, 'password': password})
#         print("Account created")
#         session['username'] = username

#         return redirect(url_for('p1'))

#     return render_template('sign-up.html')



# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'username' not in session:
#             flash("Please log in to access this page.")
#             return redirect(url_for('login'))
#         return f(*args, **kwargs)
#     return decorated_function

# @app.route('/tell-us-about-yourself', methods=["GET", "POST"])
# @login_required 
# def p1():
#     if request.method == "POST":
#         selected_dream = request.form.get('dream')
#         final_dream = None
#         if selected_dream:
#             if selected_dream == "Other":
#                 final_dream = request.form.get('other-dream')
#                 if not final_dream:
#                      flash("Please enter your dream in the 'Other' field.", "danger")
#                      return redirect(url_for('p1'))
#             else:
#                 final_dream = selected_dream
#         else:
#             flash("Please select a dream option.", "danger")
#             return redirect(url_for('p1'))


#         username = session.get('username')
#         if username and final_dream is not None:
#             user = users_collection.find_one({"username": username})
#             if user:
#                 users_collection.update_one(
#                     {"username": username},
#                     {"$set": {"aim": final_dream}}
#                 )
#                 flash("Your preferences have been saved!", "success")
#                 return redirect(url_for('login'))
#             else:
#                 flash("User not found. Please log in first.", "danger")
#                 return redirect(url_for('login'))
#         else:
#             flash("Could not save preference. Please try logging in again.", "danger")
#             return redirect(url_for('login'))

#     return render_template("p1.html")


# @app.route('/', methods=['GET','POST'])
# def login():
#     if request.method=="POST":
#         username = request.form['username']
#         password = request.form['password']
#         user = users_collection.find_one({'username': username})
#         if user and user['password'] == password:
#             session['username'] = username
#             session['leadership_chat_history'] = []
#             return redirect(url_for('main'))
#         else:
#             return redirect(url_for("err"))
#     return render_template("login.html")


# @app.route('/logout')
# @login_required
# def logout():
#     session.pop('username', None)
#     session.pop('leadership_chat_history', None) 
#     return redirect(url_for('login'))


# @app.route('/main')
# @login_required
# def main():
#     return render_template('main.html')


# @app.route('/dashboard')
# @login_required
# def dashboard():
#     return render_template("dashboard.html")


# @app.route('/dna-mapping')
# @login_required
# def dna():
#     ai_response = session.pop('ai_response', None)
#     suggested_career = session.pop('suggested_career', None) 
#     return render_template('dnamap.html', ai_response=ai_response, suggested_career=suggested_career)


# @app.route('/analyse-dna', methods=['POST'])
# @login_required
# def analyse_dna():
#     if request.method == 'POST':
#         stream = request.form.get('stream')
#         interests = request.form.get('interests')
#         creativity = request.form.get('creativity')
#         logic = request.form.get('logic')
#         communication = request.form.get('communication')
#         leadership = request.form.get('leadership')
#         curiosity = request.form.get('curiosity')
#         prompt_text = f"""As a career counselor, analyze the following user inputs and provide career recommendations and insights based on their Stream, Interests, and self-rated skills.

# User Inputs:
# Stream: {stream}
# Interests: {interests}
# Creativity (out of 10): {creativity}
# Logic (out of 10): {logic}
# Communication (out of 10): {communication}
# Leadership (out of 10): {leadership}
# Curiosity (out of 10): {curiosity}

# Please provide a detailed analysis and suggest potential career paths that align with these factors. **Start your response by clearly stating the primary recommended career and enclose it EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER]**. For example: "Based on your profile, your primary recommended career is [CAREERSYNC_CAREER]Software Engineer[/CAREERSYNC_CAREER]. This role typically involves..." Provide the response in a clear, well-formatted manner, suitable for display.
# """
#         system_message = """You are a helpful career counselor analyzing user profiles. Provide a response which is elaborate and interactive and fun, results should NOT BE DRY.
#         Include the primary recommended career enclosed EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER] within your response as instructed by the user prompt.
#         """

#         try:
#             response = openai_client.chat.completions.create(
#                 model="ft:gpt-4.1-mini-2025-04-14:personal:careersync:BUW1r4fH", 
#                 messages=[
#                     {"role": "system", "content": system_message},
#                     {"role": "user", "content": prompt_text}
#                 ],
#                 max_tokens=1000,
#                 temperature=0.7
#             )

#             model_response_text = response.choices[0].message.content
#             career_match = re.search(r'\[CAREERSYNC_CAREER\](.*?)\[/CAREERSYNC_CAREER\]', model_response_text, re.DOTALL)

#             suggested_career = None
#             if career_match:
#                 suggested_career = career_match.group(1).strip()
#                 model_response_for_display = re.sub(r'\[CAREERSYNC_CAREER\].*?\[/CAREERSYNC_CAREER\]', suggested_career, model_response_text, flags=re.DOTALL)
#             else:
#                 print("Warning: CAREERSYNC_CAREER tags not found in LLM response. Client-side heuristic may be used.")
#                 model_response_for_display = model_response_text 
#             session['ai_response'] = model_response_for_display
#             session['suggested_career'] = suggested_career 
#             print(f"Backend Extracted Career: {suggested_career}")
#             return redirect(url_for('dna'))

#         except Exception as e:
#             print(f"Error calling OpenAI API for DNA Mapping: {e}")
#             session['ai_response'] = f"An error occurred during analysis: {e}"
#             session['suggested_career'] = None # Ensure no career is passed on error
#             return redirect(url_for('dna'))


# @app.route('/future-you')
# @login_required
# def future():
#     envision_response = session.pop('envision_response', None)
#     return render_template("future_you.html", envision_response=envision_response)


# @app.route('/envision-career', methods=['POST'])
# @login_required
# def envision_career():
#     if request.method == 'POST':
#         chosen_career = request.form.get('career')

#         if not chosen_career or chosen_career.lower() == 'career not found': # Added check for fallback text
#              flash("Could not determine the career to envision. Please perform the DNA mapping again.", "warning")
#              return redirect(url_for('future'))

#         prompt_text = f"""As a career guidance AI, provide a detailed vision for a user envisioning themselves in the career of a "{chosen_career}".

# Describe the following aspects:
# 1.  **A Typical Day in the Life:** What would a typical day look like for someone in this role?
# 2.  **Annual Pay:** Provide a realistic range for annual salary. Mention factors that influence pay (experience, location, industry). Include an estimate of inflation-adjusted salary for the next few years (2026, 2027, 2028), clearly stating assumptions or that these are estimates.
# 3.  **Best Countries:** List some of the top countries globally to pursue this career, considering job opportunities, industry strength, and quality of life.
# 4.  **Relevant Colleges/Courses:** Suggest types of degrees, specific courses, or top universities/institutions that would be beneficial for pursuing this career.

# Format the response clearly using Markdown. Use headings (##), bold text (**), and lists (-) where appropriate. Ensure the response is well-structured and easy to read with clear sections.
# """
#         try:
#             response = openai_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are a helpful AI assistant providing career envisioning details. Format your response using Markdown, including headings (##), bold text (**), and lists (-) for clarity. Provide the inflation-adjusted salary estimates as requested, clearly stating they are estimates based on current trends."},
#                     {"role": "user", "content": prompt_text}
#                 ],
#                 max_tokens=1800,
#                 temperature=0.7
#             )

#             model_response = response.choices[0].message.content
#             session['envision_response'] = model_response

#             print("\n--- Future You AI Response ---")
#             print(f"Envisioning career: {chosen_career}")
#             print(model_response)
#             print("------------------------------\n")
#             return redirect(url_for('future'))

#         except Exception as e:
#             print(f"Error calling OpenAI API for Future You: {e}")
#             flash(f"An error occurred while envisioning your future: {e}", "danger")
#             session['envision_response'] = f"Error: Could not generate envisioned future. {e}"
#             return redirect(url_for('future'))




# @app.route('/leadership-lab')
# @login_required
# def leader():
#      session['leadership_chat_history'] = []
#      return render_template("leadership.html")

# @app.route('/send-leadership-prompt', methods=['POST'])
# @login_required
# def send_leadership_prompt():
#     data = request.json
#     user_message = data.get('user_message')
#     skill = data.get('skill')
#     if not user_message or not skill:
#         return jsonify({"error": "Missing user message or skill"}), 400

#     scenario = LEADERSHIP_SCENARIOS.get(skill)
#     if not scenario:
#         return jsonify({"error": "Invalid skill selected"}), 400

#     chat_history = session.get('leadership_chat_history', [])
#     chat_history.append({"role": "user", "content": user_message})
#     system_message = f"""You are an AI role-playing assistant for practicing "{skill}" skills.
# Your role is to act as "{scenario['persona']}" in the following scenario:
# {scenario['context']}

# Before each response as the persona, you MUST provide a rating out of 10 for the user's *previous* message based on their application of "{skill}" principles in this scenario. Format the rating clearly in bold brackets, e.g., **[Rating: X/10]**.
# After the rating (just a rating out of 10, you are not supposed to elaborate on the rating just continue with your response), provide your response in character (You will either be Sarah or John in either of the cases but you wont refer to yourself as David or anyone else), continuing the role-play.
# Keep responses concise but realistic for the role-play.
# """

#     messages = [{"role": "system", "content": system_message}]
#     messages.extend(chat_history)


#     print("\n--- OpenAI Prompt ---")
#     print(f"System: {system_message}")
#     for msg in messages:
#          print(f"{msg['role']}: {msg['content']}")
#     print("---------------------\n")


#     try:
#         response = openai_client.chat.completions.create(
#             model="gpt-4.1", 
#             messages=messages,
#             max_tokens=300, 
#             temperature=0.8 
#         )

#         ai_response_content = response.choices[0].message.content.strip()

#         print("\n--- Raw AI Response ---")
#         print(ai_response_content)
#         print("-----------------------\n")
#         chat_history.append({"role": "assistant", "content": ai_response_content})
#         session['leadership_chat_history'] = chat_history 
#         return jsonify({"ai_response": ai_response_content, "updated_history": chat_history}) 

#     except Exception as e:
#         print(f"Error calling OpenAI API for Leadership Lab: {e}")
#         error_message = f"An error occurred: {e}"
#         chat_history.append({"role": "assistant", "content": f"[Error] {error_message}"})
#         session['leadership_chat_history'] = chat_history 
#         return jsonify({"error": error_message, "ai_response": f"[Error] {error_message}", "updated_history": chat_history}), 500

# @app.route('/end-leadership-scenario', methods=['POST'])
# @login_required
# def end_leadership_scenario():
#     data = request.json
#     skill = data.get('skill')
#     chat_history = data.get('history', [])

#     if not skill or not chat_history:
#         return jsonify({"error": "Missing skill or chat history"}), 400

#     scenario = LEADERSHIP_SCENARIOS.get(skill)
#     if not scenario:
#         return jsonify({"error": "Invalid skill provided"}), 400
#     feedback_prompt = f"""You have completed a role-playing scenario for "{skill}" practice.
# Based on the following conversation history in which you played the role of "{scenario['persona']}", evaluate the user's performance as the leader/team lead.

# Provide your feedback in a clear, well-formatted manner, suitable for display in a popup.
# Include:
# 1. An overall rating out of 10 for the user's performance throughout the scenario.
# 2. Specific feedback on their strengths demonstrated during the conversation.
# 3. Concrete, actionable tips for improvement for future scenarios or real-life situations.

# Structure your response using Markdown, with clear headings for each section (Overall Rating, Strengths, Tips for Improvement).

# Conversation History:
# """

#     history_text = "\n".join([f"{turn['role'].capitalize()}: {turn['content']}" for turn in chat_history])
#     final_prompt = feedback_prompt + history_text
#     messages = [
#          {"role": "system", "content": "You are an AI providing constructive feedback on a user's leadership/communication practice scenario. Provide a clear, well-structured evaluation in Markdown."},
#          {"role": "user", "content": final_prompt}
#     ]

#     print("\n--- Feedback Prompt ---")
#     print(f"System: You are an AI providing constructive feedback...")
#     print(f"User: {final_prompt[:500]}...") 
#     print("---------------------------\n")


#     try:
#         response = openai_client.chat.completions.create(
#              model="gpt-4.1",
#              messages=messages,
#              max_tokens=500, 
#              temperature=0.7 
#         )

#         feedback_content = response.choices[0].message.content.strip()

#         print("\n--- Raw Feedback Response ---")
#         print(feedback_content)
#         print("---------------------------\n")
#         session.pop('leadership_chat_history', None)

#         return jsonify({"feedback": feedback_content})

#     except Exception as e:
#         print(f"Error generating feedback: {e}")
#         # Still clear history even on error
#         session.pop('leadership_chat_history', None)
#         return jsonify({"error": f"Could not generate feedback: {e}", "feedback": f"An error occurred while generating feedback: {e}"}), 500


# @app.route('/gradescope')
# @login_required
# def gradescope():
#      return render_template("gradescope.html")

# @app.route('/upload-reportcard', methods=['POST'])
# @login_required
# def upload_reportcard():
#     if 'report_card' not in request.files:
#         return jsonify({"error": "No file part in the request"}), 400

#     file = request.files['report_card']

#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400

#     if file:
#         try:
#             image_bytes = file.read()
#             base64_image = base64.b64encode(image_bytes).decode('utf-8')
#             prompt_text = """Analyze the provided report card image. Based on the subjects and grades visible, recommend a suitable academic stream (Science, Commerce, or Arts) for the student. Provide a short, elaborate reason for your recommendation, highlighting strengths indicated by the grades.

#             Output format:
#             Recommended Stream: [Stream Name]
#             Reason: [Short, elaborate reason based on grades]
#             """

#             response = openai_client.chat.completions.create(
#                 model="gpt-4o", 
#                 messages=[
#                     {"role": "system", "content": "You are an AI career advisor specializing in academic stream recommendations based on report cards."},
#                     {"role": "user", "content": [
#                         {"type": "text", "text": prompt_text},
#                         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}} # Assuming JPEG format, adjust if needed
#                     ]}
#                 ],
#                 max_tokens=300, 
#                 temperature=0.5
#             )

#             analysis_result = response.choices[0].message.content.strip()

#             print("\n--- Report Card Analysis Result ---")
#             print(analysis_result)
#             print("-----------------------------------\n")
#             session['last_report_card_analysis'] = analysis_result

#             return jsonify({"analysis": analysis_result})

#         except Exception as e:
#             print(f"Error processing report card: {e}")
#             return jsonify({"error": f"Failed to analyze report card: {e}"}), 500

#     return jsonify({"error": "Something went wrong with the file upload."}), 500

# # New route to handle follow-up questions
# @app.route('/ask-followup', methods=['POST'])
# @login_required
# def ask_followup():
#     data = request.json
#     question = data.get('question')
#     analysis_context = data.get('analysis_context') # Get the previous analysis from the frontend

#     if not question:
#         return jsonify({"error": "No question provided"}), 400

#     if not analysis_context:
#          return jsonify({"error": "No previous analysis context found. Please upload a report card first."}), 400


#     try:
#         # Construct the prompt with the previous analysis as context
#         prompt_text = f"""Based on the previous report card analysis:
# {analysis_context}

# The user has a follow-up question: "{question}"

# Please answer the user's follow-up question, referencing the report card analysis provided. Keep the answer concise and relevant.
# """

#         response = openai_client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are an AI career advisor answering follow-up questions based on a previous report card analysis."},
#                 {"role": "user", "content": prompt_text}
#             ],
#             max_tokens=200, 
#             temperature=0.7
#         )

#         followup_answer = response.choices[0].message.content.strip()

#         print("\n--- Follow-up Question Answer ---")
#         print(followup_answer)
#         print("---------------------------------\n")


#         return jsonify({"answer": followup_answer})

#     except Exception as e:
#         print(f"Error processing follow-up question: {e}")
#         return jsonify({"error": f"Failed to answer follow-up question: {e}"}), 500


# if __name__ == '__main__':
#     if not os.path.exists('templates'):
#         os.makedirs('templates')

#     app.run(debug=True, port=7479)




# from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# from pymongo import MongoClient
# from functools import wraps
# import certifi
# import os
# from openai import OpenAI
# import re 
# import base64 

# app = Flask(__name__)
# app.secret_key = '123'
# client = MongoClient(
#     "uri",
#     tls=True,
#     tlsCAFile=certifi.where()
# )

# db = client['NexusLMB']
# users_collection = db['user_data']
# openai_api_key = os.environ.get("OPENAI_API_KEY")
# if not openai_api_key:
#      print("OPENAI_API_KEY environment variable not set. Using hardcoded key (less secure).")
#      openai_api_key = "api"
# openai_client = OpenAI(api_key=openai_api_key)

# LEADERSHIP_SCENARIOS = {
#     "Effective Communication": {
#         "persona": "John, a junior employee who is struggling with performance and deadlines.",
#         "context": "You are a team lead talking to John, a junior employee, about his poor performance and consistent delays. Your goal is to address the issue constructively, understand his challenges, and set clear expectations. Respond as John."
#     },
#     "Leadership": {
#         "persona": "Sarah and David, two team members in conflict.",
#         "context": "You are mediating a conflict between two team members, Sarah and David. Your goal is to understand both sides and find a resolution. Respond alternately as Sarah and David, or in a way that shows interaction between them."
#     }
# }

# @app.route('/error', methods=['GET'])
# def err():
#     return render_template('error.html')

# @app.route('/sign-up', methods=['GET', 'POST'])
# def sign():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if users_collection.find_one({'username': username}):
#             flash('Username already exists. Try another one.')
#             return redirect(url_for('sign'))
#         users_collection.insert_one({'username': username, 'password': password})
#         print("Account created")
#         session['username'] = username

#         return redirect(url_for('p1'))

#     return render_template('sign-up.html')



# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'username' not in session:
#             flash("Please log in to access this page.")
#             return redirect(url_for('login'))
#         return f(*args, **kwargs)
#     return decorated_function

# @app.route('/tell-us-about-yourself', methods=["GET", "POST"])
# @login_required 
# def p1():
#     if request.method == "POST":
#         selected_dream = request.form.get('dream')
#         final_dream = None
#         if selected_dream:
#             if selected_dream == "Other":
#                 final_dream = request.form.get('other-dream')
#                 if not final_dream:
#                      flash("Please enter your dream in the 'Other' field.", "danger")
#                      return redirect(url_for('p1'))
#             else:
#                 final_dream = selected_dream
#         else:
#             flash("Please select a dream option.", "danger")
#             return redirect(url_for('p1'))


#         username = session.get('username')
#         if username and final_dream is not None:
#             user = users_collection.find_one({"username": username})
#             if user:
#                 users_collection.update_one(
#                     {"username": username},
#                     {"$set": {"aim": final_dream}}
#                 )
#                 flash("Your preferences have been saved!", "success")
#                 return redirect(url_for('login'))
#             else:
#                 flash("User not found. Please log in first.", "danger")
#                 return redirect(url_for('login'))
#         else:
#             flash("Could not save preference. Please try logging in again.", "danger")
#             return redirect(url_for('login'))

#     return render_template("p1.html")


# @app.route('/', methods=['GET','POST'])
# def login():
#     if request.method=="POST":
#         username = request.form['username']
#         password = request.form['password']
#         user = users_collection.find_one({'username': username})
#         if user and user['password'] == password:
#             session['username'] = username
#             session['leadership_chat_history'] = []
#             return redirect(url_for('main'))
#         else:
#             return redirect(url_for("err"))
#     return render_template("login.html")


# @app.route('/logout')
# @login_required
# def logout():
#     session.pop('username', None)
#     session.pop('leadership_chat_history', None) 
#     return redirect(url_for('login'))


# @app.route('/main')
# @login_required
# def main():
#     return render_template('main.html')


# @app.route('/dashboard')
# @login_required
# def dashboard():
#     return render_template("dashboard.html")


# @app.route('/dna-mapping')
# @login_required
# def dna():
#     ai_response = session.pop('ai_response', None)
#     suggested_career = session.pop('suggested_career', None) 
#     return render_template('dnamap.html', ai_response=ai_response, suggested_career=suggested_career)


# @app.route('/analyse-dna', methods=['POST'])
# @login_required
# def analyse_dna():
#     if request.method == 'POST':
#         stream = request.form.get('stream')
#         interests = request.form.get('interests')
#         creativity = request.form.get('creativity')
#         logic = request.form.get('logic')
#         communication = request.form.get('communication')
#         leadership = request.form.get('leadership')
#         curiosity = request.form.get('curiosity')
#         prompt_text = f"""As a career counselor, analyze the following user inputs and provide career recommendations and insights based on their Stream, Interests, and self-rated skills.

# User Inputs:
# Stream: {stream}
# Interests: {interests}
# Creativity (out of 10): {creativity}
# Logic (out of 10): {logic}
# Communication (out of 10): {communication}
# Leadership (out of 10): {leadership}
# Curiosity (out of 10): {curiosity}

# Please provide a detailed analysis and suggest potential career paths that align with these factors. **Start your response by clearly stating the primary recommended career and enclose it EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER]**. For example: "Based on your profile, your primary recommended career is [CAREERSYNC_CAREER]Software Engineer[/CAREERSYNC_CAREER]. This role typically involves..." Provide the response in a clear, well-formatted manner, suitable for display.
# """
#         system_message = """You are a helpful career counselor analyzing user profiles. Provide a response which is elaborate and interactive and fun, results should NOT BE DRY.
#         Include the primary recommended career enclosed EXACTLY within the tags [CAREERSYNC_CAREER] and [/CAREERSYNC_CAREER] within your response as instructed by the user prompt.
#         """

#         try:
#             response = openai_client.chat.completions.create(
#                 model="ft:gpt-4.1-mini-2025-04-14:personal:careersync:BUW1r4fH", 
#                 messages=[
#                     {"role": "system", "content": system_message},
#                     {"role": "user", "content": prompt_text}
#                 ],
#                 max_tokens=1000,
#                 temperature=0.7
#             )

#             model_response_text = response.choices[0].message.content
#             career_match = re.search(r'\[CAREERSYNC_CAREER\](.*?)\[/CAREERSYNC_CAREER\]', model_response_text, re.DOTALL)

#             suggested_career = None
#             if career_match:
#                 suggested_career = career_match.group(1).strip()
#                 model_response_for_display = re.sub(r'\[CAREERSYNC_CAREER\].*?\[/CAREERSYNC_CAREER\]', suggested_career, model_response_text, flags=re.DOTALL)
#             else:
#                 print("Warning: CAREERSYNC_CAREER tags not found in LLM response. Client-side heuristic may be used.")
#                 model_response_for_display = model_response_text 
#             session['ai_response'] = model_response_for_display
#             session['suggested_career'] = suggested_career 
#             print(f"Backend Extracted Career: {suggested_career}")
#             return redirect(url_for('dna'))

#         except Exception as e:
#             print(f"Error calling OpenAI API for DNA Mapping: {e}")
#             session['ai_response'] = f"An error occurred during analysis: {e}"
#             session['suggested_career'] = None # Ensure no career is passed on error
#             return redirect(url_for('dna'))


# @app.route('/future-you')
# @login_required
# def future():
#     envision_response = session.pop('envision_response', None)
#     return render_template("future_you.html", envision_response=envision_response)


# @app.route('/envision-career', methods=['POST'])
# @login_required
# def envision_career():
#     if request.method == 'POST':
#         chosen_career = request.form.get('career')

#         if not chosen_career or chosen_career.lower() == 'career not found': # Added check for fallback text
#              flash("Could not determine the career to envision. Please perform the DNA mapping again.", "warning")
#              return redirect(url_for('future'))

#         prompt_text = f"""As a career guidance AI, provide a detailed vision for a user envisioning themselves in the career of a "{chosen_career}".

# Describe the following aspects:
# 1.  **A Typical Day in the Life:** What would a typical day look like for someone in this role?
# 2.  **Annual Pay:** Provide a realistic range for annual salary. Mention factors that influence pay (experience, location, industry). Include an estimate of inflation-adjusted salary for the next few years (2026, 2027, 2028), clearly stating assumptions or that these are estimates.
# 3.  **Best Countries:** List some of the top countries globally to pursue this career, considering job opportunities, industry strength, and quality of life.
# 4.  **Relevant Colleges/Courses:** Suggest types of degrees, specific courses, or top universities/institutions that would be beneficial for pursuing this career.

# Format the response clearly using Markdown. Use headings (##), bold text (**), and lists (-) where appropriate. Ensure the response is well-structured and easy to read with clear sections.
# """
#         try:
#             response = openai_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are a helpful AI assistant providing career envisioning details. Format your response using Markdown, including headings (##), bold text (**), and lists (-) for clarity. Provide the inflation-adjusted salary estimates as requested, clearly stating they are estimates based on current trends."},
#                     {"role": "user", "content": prompt_text}
#                 ],
#                 max_tokens=1800,
#                 temperature=0.7
#             )

#             model_response = response.choices[0].message.content
#             session['envision_response'] = model_response

#             print("\n--- Future You AI Response ---")
#             print(f"Envisioning career: {chosen_career}")
#             print(model_response)
#             print("------------------------------\n")
#             return redirect(url_for('future'))

#         except Exception as e:
#             print(f"Error calling OpenAI API for Future You: {e}")
#             flash(f"An error occurred while envisioning your future: {e}", "danger")
#             session['envision_response'] = f"Error: Could not generate envisioned future. {e}"
#             return redirect(url_for('future'))




# @app.route('/leadership-lab')
# @login_required
# def leader():
#      session['leadership_chat_history'] = []
#      return render_template("leadership.html")

# @app.route('/send-leadership-prompt', methods=['POST'])
# @login_required
# def send_leadership_prompt():
#     data = request.json
#     user_message = data.get('user_message')
#     skill = data.get('skill')
#     if not user_message or not skill:
#         return jsonify({"error": "Missing user message or skill"}), 400

#     scenario = LEADERSHIP_SCENARIOS.get(skill)
#     if not scenario:
#         return jsonify({"error": "Invalid skill selected"}), 400

#     chat_history = session.get('leadership_chat_history', [])
#     chat_history.append({"role": "user", "content": user_message})
#     system_message = f"""You are an AI role-playing assistant for practicing "{skill}" skills.
# Your role is to act as "{scenario['persona']}" in the following scenario:
# {scenario['context']}

# Before each response as the persona, you MUST provide a rating out of 10 for the user's *previous* message based on their application of "{skill}" principles in this scenario. Format the rating clearly in bold brackets, e.g., **[Rating: X/10]**.
# After the rating (just a rating out of 10, you are not supposed to elaborate on the rating just continue with your response), provide your response in character (You will either be Sarah or John in either of the cases but you wont refer to yourself as David or anyone else), continuing the role-play.
# Keep responses concise but realistic for the role-play.
# """

#     messages = [{"role": "system", "content": system_message}]
#     messages.extend(chat_history)


#     print("\n--- OpenAI Prompt ---")
#     print(f"System: {system_message}")
#     for msg in messages:
#          print(f"{msg['role']}: {msg['content']}")
#     print("---------------------\n")


#     try:
#         response = openai_client.chat.completions.create(
#             model="gpt-4.1", 
#             messages=messages,
#             max_tokens=300, 
#             temperature=0.8 
#         )

#         ai_response_content = response.choices[0].message.content.strip()

#         print("\n--- Raw AI Response ---")
#         print(ai_response_content)
#         print("-----------------------\n")
#         chat_history.append({"role": "assistant", "content": ai_response_content})
#         session['leadership_chat_history'] = chat_history 
#         return jsonify({"ai_response": ai_response_content, "updated_history": chat_history}) 

#     except Exception as e:
#         print(f"Error calling OpenAI API for Leadership Lab: {e}")
#         error_message = f"An error occurred: {e}"
#         chat_history.append({"role": "assistant", "content": f"[Error] {error_message}"})
#         session['leadership_chat_history'] = chat_history 
#         return jsonify({"error": error_message, "ai_response": f"[Error] {error_message}", "updated_history": chat_history}), 500

# @app.route('/end-leadership-scenario', methods=['POST'])
# @login_required
# def end_leadership_scenario():
#     data = request.json
#     skill = data.get('skill')
#     chat_history = data.get('history', [])

#     if not skill or not chat_history:
#         return jsonify({"error": "Missing skill or chat history"}), 400

#     scenario = LEADERSHIP_SCENARIOS.get(skill)
#     if not scenario:
#         return jsonify({"error": "Invalid skill provided"}), 400
#     feedback_prompt = f"""You have completed a role-playing scenario for "{skill}" practice.
# Based on the following conversation history in which you played the role of "{scenario['persona']}", evaluate the user's performance as the leader/team lead.

# Provide your feedback in a clear, well-formatted manner, suitable for display in a popup.
# Include:
# 1. An overall rating out of 10 for the user's performance throughout the scenario.
# 2. Specific feedback on their strengths demonstrated during the conversation.
# 3. Concrete, actionable tips for improvement for future scenarios or real-life situations.

# Structure your response using Markdown, with clear headings for each section (Overall Rating, Strengths, Tips for Improvement).

# Conversation History:
# """

#     history_text = "\n".join([f"{turn['role'].capitalize()}: {turn['content']}" for turn in chat_history])
#     final_prompt = feedback_prompt + history_text
#     messages = [
#          {"role": "system", "content": "You are an AI providing constructive feedback on a user's leadership/communication practice scenario. Provide a clear, well-structured evaluation in Markdown."},
#          {"role": "user", "content": final_prompt}
#     ]

#     print("\n--- Feedback Prompt ---")
#     print(f"System: You are an AI providing constructive feedback...")
#     print(f"User: {final_prompt[:500]}...") 
#     print("---------------------------\n")


#     try:
#         response = openai_client.chat.completions.create(
#              model="gpt-4.1",
#              messages=messages,
#              max_tokens=500, 
#              temperature=0.7 
#         )

#         feedback_content = response.choices[0].message.content.strip()

#         print("\n--- Raw Feedback Response ---")
#         print(feedback_content)
#         print("---------------------------\n")
#         session.pop('leadership_chat_history', None)

#         return jsonify({"feedback": feedback_content})

#     except Exception as e:
#         print(f"Error generating feedback: {e}")
#         # Still clear history even on error
#         session.pop('leadership_chat_history', None)
#         return jsonify({"error": f"Could not generate feedback: {e}", "feedback": f"An error occurred while generating feedback: {e}"}), 500


# @app.route('/gradescope')
# @login_required
# def gradescope():
#      return render_template("gradescope.html")

# @app.route('/upload-reportcard', methods=['POST'])
# @login_required
# def upload_reportcard():
#     if 'report_card' not in request.files:
#         return jsonify({"error": "No file part in the request"}), 400

#     file = request.files['report_card']

#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400

#     if file:
#         try:
#             image_bytes = file.read()
#             base64_image = base64.b64encode(image_bytes).decode('utf-8')
#             prompt_text = """Analyze the provided report card image. Based on the subjects and grades visible, recommend a suitable academic stream (Science, Commerce, or Arts) for the student. Provide a short, elaborate reason for your recommendation, highlighting strengths indicated by the grades.

#             Output format:
#             Recommended Stream: [Stream Name]
#             Reason: [Short, elaborate reason based on grades]
#             """

#             response = openai_client.chat.completions.create(
#                 model="gpt-4o", 
#                 messages=[
#                     {"role": "system", "content": "You are an AI career advisor specializing in academic stream recommendations based on report cards."},
#                     {"role": "user", "content": [
#                         {"type": "text", "text": prompt_text},
#                         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}} # Assuming JPEG format, adjust if needed
#                     ]}
#                 ],
#                 max_tokens=300, 
#                 temperature=0.5
#             )

#             analysis_result = response.choices[0].message.content.strip()

#             print("\n--- Report Card Analysis Result ---")
#             print(analysis_result)
#             print("-----------------------------------\n")
#             session['last_report_card_analysis'] = analysis_result

#             return jsonify({"analysis": analysis_result})

#         except Exception as e:
#             print(f"Error processing report card: {e}")
#             return jsonify({"error": f"Failed to analyze report card: {e}"}), 500

#     return jsonify({"error": "Something went wrong with the file upload."}), 500

# # New route to handle follow-up questions
# @app.route('/ask-followup', methods=['POST'])
# @login_required
# def ask_followup():
#     data = request.json
#     question = data.get('question')
#     analysis_context = data.get('analysis_context') # Get the previous analysis from the frontend

#     if not question:
#         return jsonify({"error": "No question provided"}), 400

#     if not analysis_context:
#          return jsonify({"error": "No previous analysis context found. Please upload a report card first."}), 400


#     try:
#         # Construct the prompt with the previous analysis as context
#         prompt_text = f"""Based on the previous report card analysis:
# {analysis_context}

# The user has a follow-up question: "{question}"

# Please answer the user's follow-up question, referencing the report card analysis provided. Keep the answer concise and relevant.
# """

#         response = openai_client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are an AI career advisor answering follow-up questions based on a previous report card analysis."},
#                 {"role": "user", "content": prompt_text}
#             ],
#             max_tokens=200, 
#             temperature=0.7
#         )

#         followup_answer = response.choices[0].message.content.strip()

#         print("\n--- Follow-up Question Answer ---")
#         print(followup_answer)
#         print("---------------------------------\n")


#         return jsonify({"answer": followup_answer})

#     except Exception as e:
#         print(f"Error processing follow-up question: {e}")
#         return jsonify({"error": f"Failed to answer follow-up question: {e}"}), 500


# if __name__ == '__main__':
#     if not os.path.exists('templates'):
#         os.makedirs('templates')

#     app.run(debug=True, port=7479)
