import gradio as gr
import os
from urllib.parse import urlparse
import tempfile
import fitz
from pdfminer.high_level import extract_text
import subprocess
import glob
import re
import datetime
import pyperclip
import shutil
import requests
import tempfile



# 이미지를 추출하는 함수
def extract_images_from_pdf(pdf_path, images_folder):
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            for img_index, img in enumerate(doc.get_page_images(page_num)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # 이미지 파일 저장
                with open(f"{images_folder}/page{page_num + 1}_img{xref}.png", "wb") as img_file:
                    img_file.write(image_bytes)
        doc.close()
        return True
    except Exception as e:
        print(f"An error occurred while extracting images: {e}")
        return False

# 텍스트를 추출하는 함수
def extract_text_from_pdf(pdf_path):
    try:
        text = extract_text(pdf_path)
        return text
    except Exception as e:
        print(f"An error occurred while extracting text: {e}")
        return None




# PDF URL에서 PDF 파일을 다운로드하는 함수
def download_pdf_from_url(pdf_url):
    response = requests.get(pdf_url)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(response.content)
        temp_file_path = temp_file.name
    return temp_file_path


# PDF 처리 함수
def process_pdf(pdf_file=None, pdf_url=None):
    if pdf_url:
        pdf_file_path = download_pdf_from_url(pdf_url)
        pdf_file_name = os.path.splitext(os.path.basename(urlparse(pdf_url).path))[0]
    elif pdf_file:
        pdf_file_path = pdf_file.name
        pdf_file_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
    else:
        return "No PDF file or URL provided.", "No PDF file or URL provided.", gr.update(visible=False), gr.update(visible=False), ""

    base_dir = f"pdf_ext_{pdf_file_name}"
    os.makedirs(base_dir, exist_ok=True)

    txt_folder = os.path.join(base_dir, "text")
    images_folder = os.path.join(base_dir, "image")
    os.makedirs(txt_folder, exist_ok=True)
    os.makedirs(images_folder, exist_ok=True)

    pdf_path = pdf_file_path

    images_result = extract_images_from_pdf(pdf_path, images_folder)
    text_result = extract_text_from_pdf(pdf_path)

    if images_result:
        images_output = f"Images extracted successfully to {images_folder}"
    else:
        images_output = "An error occurred while extracting images."

    if text_result:
        return images_output, text_result, gr.update(visible=True), gr.update(visible=True), pdf_file_name
    else:
        return images_output, "An error occurred while extracting text.", gr.update(visible=False), gr.update(visible=False), pdf_file_name



pdf_folder = gr.File(label="Select PDF Folder")
# 배치 PDF 처리 함수

def process_batch_pdf(pdf_folder):
    if not pdf_folder:  # Check if the input list is empty
        return "No files selected.", ""
    
    try:
        processed_files = []
        for pdf_file_path in pdf_folder:
            # Ensure the path is a file, not a directory
            if not os.path.isfile(pdf_file_path):
                return f"Provided path '{pdf_file_path}' is not a file.", ""
            
            # Process each PDF file using the process_pdf function
            images_output, text_output, _, _, pdf_file_name = process_pdf(pdf_file=pdf_file_path)
            processed_files.append(f"File: {pdf_file_name}\nImages: {images_output}\nText: {text_output}\n\n")
            
            # Remove the processed PDF file's directory
            pdf_dir = f"pdf_ext_{pdf_file_name}"
            if os.path.exists(pdf_dir):
                shutil.rmtree(pdf_dir)
        
        # Generate the markdown file path
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file_path = os.path.join(os.getcwd(), f"batch_processed_{current_time}.md")
        
        # Save the processed files' information to the markdown file
        with open(md_file_path, "w", encoding="utf-8") as md_file:
            md_file.write("# Batch Processed PDF Files\n\n")
            md_file.write("".join(processed_files))
        
        return f"Batch processing completed. Markdown file saved at: {md_file_path}", md_file_path
    except Exception as e:
        return f"An error occurred during batch processing: {e}", ""






# 텍스트를 클립보드에 복사하는 함수
def copy_text_to_clipboard(text):
    pyperclip.copy(text)
    return "Text copied to clipboard!"

def download_text(text, pdf_file_name):
    base_dir = f"pdf_ext_{pdf_file_name}"
    txt_folder = os.path.join(base_dir, "text")
    
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    text_file_path = os.path.join(txt_folder, f"extracted_text_{current_time}.txt")
    with open(text_file_path, "w", encoding="utf-8") as file:
        file.write(text)
    return text_file_path


    



# 비디오 다운로드 함수
def download_video(url, output_path):
    command = f'yt-dlp "{url}" -o "{output_path}"'
    subprocess.run(command, shell=True, check=True)

# 자막 다운로드 및 처리 함수
def download_and_process_subtitles(url, lang_code):
    yt_down_folder_path = ensure_yt_down_folder_exists()  # yt_down 폴더 확인 및 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        command = f'yt-dlp --skip-download --write-subs --write-auto-subs --sub-lang {lang_code} --convert-subs srt "{url}" -o "{temp_dir}/%(title)s.%(ext)s"'
        subprocess.run(command, shell=True, check=True)
        subtitle_files = glob.glob(f"{temp_dir}/*.{lang_code}.srt")
        if not subtitle_files:
            return "선택한 언어의 자막 파일을 찾을 수 없습니다."
        subtitles = ""
        last_line = None
        for subtitle_file in subtitle_files:
            final_subtitle_path = os.path.join(yt_down_folder_path, os.path.basename(subtitle_file)) # 최종 자막 파일 경로 수정
            shutil.move(subtitle_file, final_subtitle_path)  # 임시 디렉터리에서 yt_down 폴더로 자막 파일 이동
            with open(final_subtitle_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = re.sub(r'\d+:\d+:\d+.\d+ --> \d+:\d+:\d+.\d+', '', line)
                    line = re.sub(r'^\d+$', '', line, flags=re.MULTILINE)
                    line = re.sub(r'<[^>]+>', '', line)
                    line = re.sub(r'^\s*$', '', line, flags=re.MULTILINE)
                    if line != last_line:
                        subtitles += line
                    last_line = line
                subtitles += "\n\n"
        return subtitles.strip()

# 중복 라인 제거 함수
def remove_duplicate_lines(subtitles):
    lines = subtitles.split("\n")
    unique_lines = []
    for line in lines:
        if line not in unique_lines:
            unique_lines.append(line)
    return "\n".join(unique_lines)

# 자막 처리 함수
def process_subtitles(url, lang_code):
    subtitles = download_and_process_subtitles(url, lang_code)
    subtitles = remove_duplicate_lines(subtitles)
    return subtitles, gr.update(visible=True), gr.update(visible=True)

# 자막을 클립보드에 복사하는 함수
def copy_to_clipboard(subtitles):
    pyperclip.copy(subtitles)
    return "Subtitles copied to clipboard!"

# 자막을 파일로 다운로드하는 함수
def download_subtitles(subtitles):
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    subtitles_file_path = os.path.join(os.getcwd(), f"subtitles_{current_time}.txt")
    with open(subtitles_file_path, "w", encoding="utf-8") as file:
        file.write(subtitles)
    return subtitles_file_path

# 비디오 파일을 다운로드하는 함수
def download_video_file(url):
    yt_down_folder_path = ensure_yt_down_folder_exists()  # yt_down 폴더 확인 및 생성
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    video_file_path = os.path.join(yt_down_folder_path, f"video_{current_time}.mp4")
    download_video(url, video_file_path)
    return f"Video downloaded successfully! File saved at: {video_file_path}"


# yt_down 폴더를 생성하는 기능 추가
def ensure_yt_down_folder_exists():
    yt_down_folder_path = os.path.join(os.getcwd(), 'yt_down')
    os.makedirs(yt_down_folder_path, exist_ok=True)
    return yt_down_folder_path



# Gradio 인터페이스 생성
with gr.Blocks() as demo:
    gr.Markdown("# PDF & Video Extractor")
    with gr.Tab("PDF Image and Text Extractor"):
        pdf_file = gr.File(label="Upload PDF File", file_types=[".pdf"])
        pdf_url = gr.Textbox(label="Enter PDF URL")
        extract_button = gr.Button("Extract Images and Text")
        images_output = gr.Textbox(label="Images Extraction Result")
        text_output = gr.Textbox(label="Extracted Text", lines=10)
        copy_text_button = gr.Button("Copy to Clipboard", visible=False)
        copy_text_output = gr.Textbox(label="Copy Status")
        download_text_button = gr.Button("Download Text", visible=False)
        pdf_file_name = gr.State()
        
        extract_button.click(process_pdf, inputs=[pdf_file, pdf_url], outputs=[images_output, text_output, copy_text_button, download_text_button, pdf_file_name])
        copy_text_button.click(copy_text_to_clipboard, inputs=text_output, outputs=copy_text_output)
        download_text_button.click(download_text, inputs=[text_output, pdf_file_name], outputs=gr.File())


    with gr.Tab("Batch PDF"):
        pdf_folder = gr.File(label="Select PDF Files", file_types=[".pdf"], file_count="multiple")
        batch_process_button = gr.Button("Process Batch PDF")
        batch_output = gr.Textbox(label="Batch Processing Result")

        batch_process_button.click(process_batch_pdf, inputs=[pdf_folder], outputs=[batch_output])
        


    with gr.Tab("Subtitle Downloader"):
        video_url = gr.Textbox(label="Enter Video URL")
        lang_dropdown = gr.Dropdown(label="Select Subtitle Language", choices=["en", "ko", "ja", "de", "fr", "es", "zh", "ru", "ar", "pt", "it", "hi", "tr", "vi"])
        subtitles_button = gr.Button("Show Subtitles")
        subtitles_output = gr.Textbox(label="Subtitles", lines=10)
        copy_button = gr.Button("Copy to Clipboard", visible=False)
        copy_output = gr.Textbox(label="Copy Status")
        download_subs_button = gr.Button("Download Subtitles", visible=False)
        download_video_button = gr.Button("Download Video")
        download_video_output = gr.Textbox(label="Download Status")
        
        subtitles_button.click(process_subtitles, inputs=[video_url, lang_dropdown], outputs=[subtitles_output, copy_button, download_subs_button])
        copy_button.click(copy_to_clipboard, inputs=subtitles_output, outputs=copy_output)
        download_subs_button.click(download_subtitles, inputs=subtitles_output, outputs=gr.File())
        download_video_button.click(download_video_file, inputs=video_url, outputs=download_video_output)

demo.launch()

