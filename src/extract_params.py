import pdfplumber

def extract_pdf_data(file_path):
    with pdfplumber.open(file_path) as pdf:
        text_content: list[str] = []
        for page in pdf.pages:
            text_content.append(page.extract_text() or "")
            tables = page.extract_tables()
            if tables:
                text_content.append("\n--- TABLES FOUND ---\n")
                for table in tables:
                    text_content.append(str(table))
        return "\n".join(text_content)

try:
    print(extract_pdf_data("Parametros UT 113:114.pdf"))

except Exception as e:
    print(f"Error: {e}")
