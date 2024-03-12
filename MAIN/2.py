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
def extract_text_from_pdf(pdf_path, output_folder):
    try:
        text = extract_text(pdf_path)
        with open(f"{output_folder}/extracted_text.txt", "w", encoding="utf-8") as text_file:
            text_file.write(text)
        return True
    except Exception as e:
        print(f"An error occurred while extracting text: {e}")
        return False


# PDF URL에서 PDF 파일을 다운로드하는 함수
def download_pdf_from_url(pdf_url):
    response = requests.get(pdf_url)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(response.content)
        temp_file_path = temp_file.name
    return temp_file_path


# PDF 처리 함수
def process_pdf(pdf_file_path=None, pdf_url=None):
    if pdf_url:
        pdf_file_path = download_pdf_from_url(pdf_url)
        pdf_file_name = os.path.splitext(os.path.basename(urlparse(pdf_url).path))[0]
    elif pdf_file_path:
        pdf_file_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
    else:
        return "No PDF file or URL provided.", "No PDF file or URL provided."

    base_dir = f"pdf_ext_{pdf_file_name}"
    os.makedirs(base_dir, exist_ok=True)

    txt_folder = os.path.join(base_dir, "text")
    images_folder = os.path.join(base_dir, "image")
    os.makedirs(txt_folder, exist_ok=True)
    os.makedirs(images_folder, exist_ok=True)

    pdf_path = pdf_file_path

    images_result = extract_images_from_pdf(pdf_path, images_folder)
    text_result = extract_text_from_pdf(pdf_path, txt_folder)

    if images_result:
        images_output = f"Images extracted successfully to {images_folder}"
    else:
        images_output = "An error occurred while extracting images."

    if text_result:
        text_output = f"Text extracted successfully to {txt_folder}/extracted_text.txt"
    else:
        text_output = "An error occurred while extracting text."

    return images_output, text_output






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
        text_output = gr.Textbox(label="Text Extraction Result")
        extract_button.click(process_pdf, inputs=[pdf_file, pdf_url], outputs=[images_output, text_output])

    
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

