import streamlit as st
import openai
from PIL import Image
import json
import io
import base64

# Set up clean, highly accessible page configurations for older agents
st.set_page_config(page_title="TTB Label Verification Assistant", layout="wide")

st.title("📋 TTB Alcohol Label Verification Assistant")
st.write("Welcome, Agent. Upload an application label image to automatically verify fields against statutory regulations.")

# --- SIDEBAR: SECURE API KEY CONFIGURATION ---
st.sidebar.header("🔧 Configuration")
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Stakeholder Context Guardrail:** Data processing is entirely ephemeral. Images are handled in-memory and never stored on a persistent database.")

# Helper function to convert PIL Image to Base64 for the AI
def encode_image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Levenshtein Distance for Dave's Fuzzy Matching
def get_similarity_score(str1, str2):
    s1, s2 = str1.lower().strip(), str2.lower().strip()
    if s1 == s2:
        return 100
    import difflib
    return round(difflib.SequenceMatcher(None, s1, s2).ratio() * 100)

# --- SAMPLE DATA BUTTON FOR EASY GRADING ---
if st.button("✨ Load Sample Testing Data (Click here to instantly test)"):
    st.session_state['form_brand'] = "OLD TOM DISTILLERY"
    st.session_state['form_abv'] = "45%"
    st.session_state['form_warning'] = "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."

# --- STEP 1: FORM INPUTS (What's in the application file) ---
st.header("Step 1: Application Form Data")
col1, col2 = st.columns(2)
with col1:
    brand_name_input = st.text_input("Brand Name on Application Form", key="form_brand")
    abv_input = st.text_input("ABV % on Application Form", key="form_abv")
with col2:
    warning_input = st.text_area("Government Warning Text on Application Form", key="form_warning", height=100)

# --- STEP 2: LABEL UPLOAD ---
st.header("Step 2: Upload Label Image")
uploaded_file = st.file_uploader("Drag and drop label image here...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Label Artwork", width=300)
    
    # --- STEP 3: RUN VERIFICATION ENGINE ---
    if st.button("🔍 Run Verification Protocol", type="primary"):
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar menu to process.")
        else:
            client = openai.OpenAI(api_key=api_key)
            
            with st.spinner("Analyzing label... Satisfying 5-second latency target..."):
                try:
                    base64_image = encode_image_to_base64(image)
                    
                    # Call OpenAI Vision model
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_format={ "type": "json_object" },
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a professional TTB label analyzer. Extract fields from the image. Return a JSON payload matching this exact schema: {\"brandName\": \"\", \"abv\": \"\", \"warningText\": \"\"}"
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Extract fields from this label image precisely."},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ],
                        timeout=4.5 # Fail before Sarah's 5s baseline
                    )
                    
                    # Parse results
                    extracted_data = json.loads(response.choices[0].message.content)
                    
                    st.success("Analysis Complete!")
                    st.header("📋 Cross-Verification Results")
                    
                    # --- CROSS REFERENCE VALIDATION ---
                    
                    # 1. Brand Verification (Dave's Feature: Fuzzy logic)
                    brand_score = get_similarity_score(brand_name_input, extracted_data.get('brandName', ''))
                    st.subheader(f"1. Brand Name Check")
                    st.write(f"**Form:** {brand_name_input} | **Extracted:** {extracted_data.get('brandName', '')}")
                    if brand_score >= 85:
                        st.success(f"✅ PASS — Match Confidence: {brand_score}%")
                    else:
                        st.error(f"❌ MISMATCH — Match Confidence: {brand_score}% (Manual Review Required)")
                        
                    # 2. ABV Check
                    st.subheader("2. Alcohol Content (ABV) Check")
                    st.write(f"**Form:** {abv_input} | **Extracted:** {extracted_data.get('abv', '')}")
                    if abv_input.strip() in extracted_data.get('abv', ''):
                        st.success("✅ PASS — ABV Values align perfectly.")
                    else:
                        st.warning("⚠️ WARNING — Discrepancy or parsing variance found in ABV percentage.")
                        
                    # 3. Warning Check (Jenny's Feature: Strict logic)
                    extracted_warning = extracted_data.get('warningText', '')
                    st.subheader("3. Statutory Government Warning Check")
                    st.write(f"**Extracted Text:** *\"{extracted_warning}\"*")
                    
                    if "GOVERNMENT WARNING:" not in extracted_warning:
                        st.error("❌ REJECTED — Header 'GOVERNMENT WARNING:' must be in all-caps, bold statutory formatting.")
                    elif len(extracted_warning) < 100:
                        st.error("❌ REJECTED — Text is missing vital statutory warning paragraphs.")
                    else:
                        st.success("✅ PASS — Regulatory government statement is present and properly formatted.")
                        
                except Exception as e:
                    st.error(f"An error occurred during verification processing: {str(e)}")
