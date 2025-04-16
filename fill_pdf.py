import streamlit as st
import fitz  # PyMuPDF
from io import BytesIO
import re

# --- Helper: Detect form-like fields from static PDF ---
def detect_fields(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    fields = []

    keywords = [
        "Name", "Date of Birth", "Race", "Religion", "Nationality",
        "Address", "Phone", "Email", "Passport", "Check-In", "Check-Out",
        "Occupation", "Age", "Medical", "Guardian"
    ]

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")['blocks']
        for b in blocks:
            if b['type'] != 0:
                continue
            for line in b['lines']:
                spans = line['spans']
                if not spans:
                    continue
                text = " ".join([span['text'] for span in spans]).strip()
                for kw in keywords:
                    if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                        x0, y0, x1, y1 = spans[0]['bbox']
                        field_x = x1 + 10
                        field_y = y0 + (y1 - y0) / 2
                        fields.append({
                            "label": text,
                            "page": page_num,
                            "pos": (field_x, field_y),
                            "x_offset": 0,
                            "y_offset": 0,
                        })
    return fields

# --- Helper: Render filled PDF ---
def fill_pdf(base_pdf, field_values, field_defs):
    doc = fitz.open(stream=base_pdf, filetype="pdf")
    for idx, f in enumerate(field_defs):
        val = field_values.get(f'label_{idx}', '')
        if val:
            page = doc[f['page']]
            x, y = f['pos']
            x += f.get('x_offset', 0)
            y += f.get('y_offset', 0)
            page.insert_text((x, y), val, fontsize=10)
    output = BytesIO()
    doc.save(output)
    return output.getvalue()

# --- Streamlit App with Tabs ---
st.set_page_config(page_title="Smart PDF Filler", layout="wide")
st.title("AI Form Filler for Static PDFs")

uploaded_file = st.file_uploader("Upload the PDF form", type="pdf")

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    field_defs = detect_fields(pdf_bytes)
    field_values = {}
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    tab1, tab2, tab3 = st.tabs(["📄 Preview Form", "📝 Fill Fields", "📥 Review & Download"])

    with tab1:
        st.header("Form Preview")
        for i, page in enumerate(doc):
            st.image(page.get_pixmap().tobytes("png"), caption=f"Page {i+1}")

    with tab2:
        st.header("Detected Fields for Input")
        if not field_defs:
            st.warning("No fields detected.")
        else:
            for i, f in enumerate(field_defs):
                st.markdown(f"**{f['label']}** (Page {f['page'] + 1})")
                field_values[f'label_{i}'] = st.text_input("", key=f"field_{i}_val")

    with tab3:
        st.header("Review Filled Form")
        if st.button("Generate Filled PDF"):
            filled_pdf_bytes = fill_pdf(pdf_bytes, field_values, field_defs)
            st.success("PDF generated.")
            filled_doc = fitz.open(stream=filled_pdf_bytes, filetype="pdf")
            for i, page in enumerate(filled_doc):
                st.image(page.get_pixmap().tobytes("png"), caption=f"Filled Page {i+1}")
            st.download_button("Download Filled Form", data=filled_pdf_bytes, file_name="filled_form.pdf", mime="application/pdf")
