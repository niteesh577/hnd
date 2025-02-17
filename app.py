import streamlit as st
import sqlite3
import os
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
from matplotlib import pyplot as plt
load_dotenv()
from streamlit.components.v1 import html
import json
import re

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_response(input_prompt, image):
    model = genai.GenerativeModel('gemini-2.0-flash-001')
    response = model.generate_content([input_prompt, image[0]])
    return response.text

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()

        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

# Database Setup
conn = sqlite3.connect('user_profiles.db')
cursor = conn.cursor()

# Create user_profiles table if not exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        weight_kg REAL,
        height_ft REAL,
        age INTEGER,
        sex TEXT,
        activity_level TEXT,
        daily_calorie_goal INTEGER
    )
''')
conn.commit()

# Function to add/update user profile
def save_user_profile(username, weight_kg, height_ft, age, sex, activity_level):
    cursor.execute('''
        INSERT OR REPLACE INTO user_profiles (username, weight_kg, height_ft, age, sex, activity_level)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (username, weight_kg, height_ft, age, sex, activity_level))
    conn.commit()

# Function to retrieve user profile
def get_user_profile(username):
    cursor.execute('SELECT * FROM user_profiles WHERE username = ?', (username,))
    return cursor.fetchone()

# Function to calculate calories
def calculate_calories(weight_kg, height_ft, age, sex, activity_level):
    # Harris-Benedict Equation
    # BMR for men: 88.362 + (13.397 * weight in kg) + (4.799 * height in cm) - (5.677 * age in years)
    # BMR for women: 447.593 + (9.247 * weight in kg) + (3.098 * height in cm) - (4.330 * age in years)

    # Convert height from feet to centimeters
    height_cm = height_ft * 30.48

    if sex.lower() == "male":
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)

    # Adjust BMR based on activity level
    activity_multipliers = {
        "sedentary": 1.2,
        "lightly active": 1.375,
        "moderately active": 1.55,
        "very active": 1.725,
        "extremely active": 1.9
    }

    total_calories = bmr * activity_multipliers.get(activity_level.lower(), 1.2)

    return total_calories

# Streamlit App
st.set_page_config(page_title="Health Tracker", page_icon=":heart:")
st.title("🌟 **Health Tracker!** 🌟")

# Sidebar navigation
page = st.sidebar.selectbox("Select Page", ["Nutrition Tracker", "Disease Detection"])

# Navigation logic
if page == "Nutrition Tracker":
    st.header("Nutrition Tracker")

    # User Profile Input
    with st.sidebar:
        st.header("User Profile")
        username = st.text_input("Enter your username:")
        weight_kg = st.number_input("Enter your weight (kg):", min_value=1.0)
        height_ft = st.number_input("Enter your height (ft):", min_value=1.0)
        age = st.number_input("Enter your age:", min_value=1, max_value=150)
        sex = st.selectbox("Select your sex:", ["Male", "Female"])
        activity_level = st.selectbox("Select your daily activity level:", ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"])

        # Save or Update User Profile
        if st.button("Save Profile"):
            save_user_profile(username, weight_kg, height_ft, age, sex, activity_level)
            st.success("Profile saved successfully!")

    # Retrieve User Profile
    saved_profile = get_user_profile(username)
    if saved_profile:
        st.sidebar.subheader("Saved Profile:")
        st.sidebar.write(f"Username: {saved_profile[1]}")
        st.sidebar.write(f"Weight: {saved_profile[2]} kg")
        st.sidebar.write(f"Height: {saved_profile[3]} ft")
        st.sidebar.write(f"Age: {saved_profile[4]} years")
        st.sidebar.write(f"Sex: {saved_profile[5]}")
        st.sidebar.write(f"Activity Level: {saved_profile[6]}")

    # Main Content
    uploaded_file = st.file_uploader("Choose an image....", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)

        submit = st.button("Tell me about the total calories")

        input_prompt = """
        You are an expert in nutritionist where you need to see the food items from the image
        and calculate the total calories, also provide the details of every food item with calories
        intake in below format

        1. Item 1 - no of calories
        2. Item 2 - no of calories

        ------
        ------
        Finally, you can also mention whether the food is healthy or not and mention the percentage split
        of the ratio of Carbohydrates,Protein,Fats,fibers,sugar, and other important things required in our diet
        """

        if submit:
            image_data = input_image_setup(uploaded_file)
            response = get_gemini_response(input_prompt, image_data)
            st.title("🌟 **The Response** 🌟")
            st.write(response)

            

            st.title("🌟 **Calorie Information** 🌟")
            st.write(f"Reminder: Total Calories needed by your body is: {total_calories} kcal")

            st.subheader("Macronutrient Distribution")
            fig, ax = plt.subplots()
            labels = ['Carbohydrates', 'Protein', 'Fats']
            sizes = [50, 20, 10]
            explode = (0.1, 0, 0)
            ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', startangle=90,
                   colors=['#FF9999', '#66B2FF', '#99FF99'])
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
            st.pyplot(fig)

elif page == "Disease Detection":
    st.header("Diagnosis Assistant")

    path = os.path.dirname(os.path.abspath(__file__))

    # Load translations from JSON file
    with open(os.path.join(path + "/Assets/translations.json")) as f:
        transl = json.load(f)

    # OpenAI API key
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


    def get_gemini_response(input_prompt):
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(input_prompt)
        return response.text




    st.markdown("""
      <style>
          .css-zck4sz p {
            font-weight: bold;
            font-size: 18px;
          }
      </style>""", unsafe_allow_html=True)

    # Add the language selection dropdown
    if 'lang_tmp' not in st.session_state:
        st.session_state['lang_tmp'] = 'English'

    if 'lang_changed' not in st.session_state:
        st.session_state['lang_changed'] = False

    if 'lang_select' in st.session_state:
        lang = st.sidebar.selectbox(transl[st.session_state['lang_select']]["language_selection"],
                                    options=list(transl.keys()), key='lang_select')
    else:
        lang = st.sidebar.selectbox(transl[st.session_state['lang_tmp']]["language_selection"],
                                    options=list(transl.keys()),
                                    key='lang_select')

    if lang != st.session_state['lang_tmp']:
        st.session_state['lang_tmp'] = lang
        st.session_state['lang_changed'] = True
    else:
        st.session_state['lang_changed'] = False

    # Line separator for clarity
    st.sidebar.markdown("""---""")

    # Font size and weight for the sidebar
    # Works with streamlit==1.17.0
    # TODO: Review class names for future versions
    st.markdown("""
      <style>
          ul[class="css-j7qwjs e1fqkh3o7"]{
            position: relative;
            padding-top: 2rem;
            display: flex;
            justify-content: center;
            flex-direction: column;
            align-items: center;
          }
          .css-17lntkn {
            font-weight: bold;
            font-size: 18px;
            color: grey;
          }
          .css-pkbazv {
            font-weight: bold;
            font-size: 18px;
          }
      </style>""", unsafe_allow_html=True)

    # Buy me a coffee - MDxApp support
    button = f"""<script type="text/javascript" src="https://cdnjs.buymeacoffee.com/1.0.0/button.prod.min.js" data-name="bmc-button" data-slug="geonosislaX" data-color="#FFDD00" data-emoji=""  data-font="Cookie" data-text="Donate now" data-outline-color="#000000" data-font-color="#000000" data-coffee-color="#ffffff" ></script>"""

    # Use GitHub logo file
    logo_name = path + "/Materials/MDxApp_logo_v2_256.png"

    # Define columns
    t1, t2 = st.columns([1, 3], gap="large")
    with t1:
        st.image(logo_name, caption='', width=256)
    with t2:
        st.header("**{}**".format(transl[lang]['page1_header']))
        st.write("<p style=\"font-weight: bold; font-size:18px;\">{}</p>".format(transl[lang]['page1_subheader']),
                 unsafe_allow_html=True)

    st.markdown("", unsafe_allow_html=True)

    # Your remaining code goes here...
    """
    ---
    """
    st.write("<p style=\"font-weight: bold; font-size:18px;\">{}</p>".format(transl[lang]['htu_0']) + \
             "<p style=\"font-size:18px;\">1. {}<br/>".format(transl[lang]['htu_1']) + \
             "2. {}<br/>".format(transl[lang]['htu_2']) + \
             "3. {}</p>".format(transl[lang]['htu_3']),
             unsafe_allow_html=True)

    st.write(
        """<style>
        [data-testid="stHorizontalBlock"] {
            align-items: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    ## Font size configs
    st.markdown(
        """<style>
    div[class*="stRadio"] > label > div[data-testid="stMarkdownContainer"] > p {
        font-size: 18px;
    }
        </style>
        """, unsafe_allow_html=True)
    st.markdown(
        """<style>
    div[class*="stNumberInput"] > label > div[data-testid="stMarkdownContainer"] > p {
        font-size: 18px;
    }
        </style>
        """, unsafe_allow_html=True)
    st.markdown(
        """<style>
    div[class*="stTextInput"] > label > div[data-testid="stMarkdownContainer"] > p {
        font-size: 18px;
    }
        </style>
        """, unsafe_allow_html=True)
    ####

    st.subheader(":black_nib: **{}**".format(transl[lang]['report_header']))
    # Define columns
    col1, col2, col3 = st.columns(3, gap="large")

    # Store initial values in session state
    if "disabled" not in st.session_state:
        st.session_state.disabled = False
    # Declare lists
    genders_list = ["{}".format(transl[lang]['male']), "{}".format(transl[lang]['female'])]
    pregnant_list = ["{}".format(transl[lang]['no']), "{}".format(transl[lang]['yes'])]
    ##

    # Gender selector
    with col1:
        if st.session_state['lang_changed'] and 'gender' in st.session_state:
            del st.session_state['gender']
        if 'gender' not in st.session_state:
            st.session_state['gender'] = genders_list[0]
        st.radio("**{}**".format(transl[lang]['gender']), genders_list, key='gender')
    # Age selector
    with col2:
        st.number_input("**{}**".format(transl[lang]['age']), min_value=0, max_value=99, step=1, key="age")
    # Pregnancy
    if st.session_state.gender == '{}'.format(transl[lang]['male']):
        st.session_state.disabled = True
        if 'pregnant' in st.session_state:
            st.session_state['pregnant'] = "{}".format(transl[lang]['no'])
    else:
        st.session_state.disabled = False

    with col3:
        if st.session_state['lang_changed'] and 'pregnant' in st.session_state:
            del st.session_state['pregnant']
        if 'pregnant' not in st.session_state:
            st.session_state['pregnant'] = pregnant_list[0]
        st.radio("**{}**".format(transl[lang]['pregnant']), pregnant_list, disabled=st.session_state.disabled,
                 key='pregnant')

    # Context
    st.text_input('**{}** *{}*'.format(transl[lang]['history'], transl[lang]['hist_example']),
                  placeholder="{}".format(transl[lang]['hist_ph']), key="context", max_chars=250,
                  help=":green[**{}**]".format(transl[lang]['hist_help']))

    # List of symptoms
    st.text_input("**{}** *{}*".format(transl[lang]['symptoms'], transl[lang]['symp_example']),
                  placeholder="{}".format(transl[lang]['symp_ph']), key="symptoms", max_chars=250,
                  help=":green[**{}**]".format(transl[lang]['symp_help']))

    # List of observations at exam
    st.text_input("**{}** *{}*".format(transl[lang]['exam'], transl[lang]['exam_example']),
                  placeholder="{}".format(transl[lang]['exam_ph']), key="exam", max_chars=250,
                  help=":green[**{}**]".format(transl[lang]['exam_help']))

    # Laboratory test results
    st.text_input("**{}** *{}*".format(transl[lang]['lab'], transl[lang]['lab_example']),
                  placeholder="{}".format(transl[lang]['lab_ph']), key="labresults", max_chars=250,
                  help=":green[**{}**]".format(transl[lang]['lab_help']))

    st.subheader(":clipboard: **{}**".format(transl[lang]['summary']))
    # Diagnostic

    report_list = [st.session_state.context, st.session_state.symptoms,
                   st.session_state.exam, st.session_state.labresults]
    corr_list = ["{}".format(transl[lang]['none']),
                 "{}".format(transl[lang]['none']),
                 "{}".format(transl[lang]['none']),
                 "{}".format(transl[lang]['none'])]
    for ic in range(0, len(report_list)):
        if report_list[ic] == "":
            report_list[ic] = corr_list[ic]

    vis_summary = "<p style=\"font-size:18px;\">" + \
                  "<b>{}</b>".format(transl[lang]['vissum_patient']) + \
                  st.session_state.gender + ", " + str(st.session_state.age) + "{}<br/>".format(
        transl[lang]['vissum_yrsold']) + \
                  "<b>{}</b>".format(transl[lang]['vissum_pregnancy']) + st.session_state.pregnant + "<br/>" + \
                  "<b>{}</b>".format(transl[lang]['vissum_history']) + report_list[0] + "<br/>" + \
                  "<b>{}</b>".format(transl[lang]['vissum_symp']) + report_list[1] + "<br/>" + \
                  "<b>{}</b>".format(transl[lang]['vissum_exam']) + report_list[2] + "<br/>" + \
                  "<b>{}</b>".format(transl[lang]['vissum_lab']) + report_list[3] + "<br/> </p>"

    st.write(vis_summary, unsafe_allow_html=True)

    prompt_words = ["Prompt word 1", "Prompt word 2", "Prompt word 3", "Prompt word 4", "Prompt word 5",
                    "Prompt word 6", "Prompt word 7", "Prompt word 8", "Prompt word 9", "Prompt word 10"]
    question_prompt = (prompt_words[0] + st.session_state.gender + ", " + \
                       str(st.session_state.age) + " years old. " + \
                       prompt_words[1] + st.session_state.pregnant + ". " + \
                       prompt_words[2] + report_list[0] + ". " + \
                       prompt_words[3] + report_list[1] + ". " + \
                       prompt_words[4] + report_list[2] + ". " + \
                       prompt_words[5] + report_list[3] + ". " + \
                       prompt_words[6] + \
                       prompt_words[7] + \
                       prompt_words[8] + \
                       prompt_words[9] + lang + ". ",
                       f"it should suspect and diagnosis what disease the person is suffering from and also recommend the suggestions for the diagnosis. it should also give me treatments for the above problem.")

    st.write('')
    submit_button = st.button('**{}**'.format(transl[lang]['submit']),
                              help=":green[**{}**]".format(transl[lang]['submit_help']))
    st.write('')

    st.subheader(":computer: :speech_balloon: :pill: **{}**".format(transl[lang]['diagnostic']))
    if submit_button:
        if report_list[1] == "{}".format(transl[lang]['none']):
            st.write("<p style=\"font-weight: bold; font-size:18px;\">{}</p>".format(transl[lang]['submit_warning']),
                     unsafe_allow_html=True)
        else:
            with st.spinner('{}'.format(transl[lang]['submit_wait'])):
                try:
                    st.session_state.diagnostic = get_gemini_response(input_prompt=question_prompt)
                    st.write('')
                    st.write(st.session_state.diagnostic.replace("", ""), unsafe_allow_html=True)
                    st.markdown(
                        """
                        ### :rotating_light: **{}** :rotating_light:
                        {}
                        """.format(transl[lang]['caution'], transl[lang]['caution_message']),
                        unsafe_allow_html=True
                    )


                except Exception as e:
                    # st.write(e)
                    st.write(
                        "<p style=\"font-weight: bold; font-size:18px;\">{}</p>".format(transl[lang]['no_response']),
                        unsafe_allow_html=True)
    else:
        if "diagnostic" in st.session_state:
            st.write(st.session_state.diagnostic.replace("", ""), unsafe_allow_html=True)
        else:
            st.write("<p style=\"font-weight: bold; font-size:18px;\">{}</p>".format(transl[lang]['no_diagnostic']),
                     unsafe_allow_html=True)

# Close the database connection when done
conn.close()
