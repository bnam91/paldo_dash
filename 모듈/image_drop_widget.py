import os
import uuid
import tempfile
import mimetypes
from PIL import ImageGrab, Image
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                            QPushButton, QFileDialog, QMessageBox, QApplication)
from PyQt5.QtCore import QUrl, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

# 인증 모듈 임포트 - 경로를 적절히 조정해야 할 수 있음
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '모집'))
from auth import get_credentials

class ImageDropWidget(QWidget):
    """이미지 드래그앤드롭 및 붙여넣기를 지원하는 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 입력 필드 및 버튼
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("이미지 URL 또는 파일을 드래그하여 놓으세요")
        
        self.button_layout = QHBoxLayout()
        self.browse_button = QPushButton("이미지 찾기...")
        self.paste_button = QPushButton("클립보드에서 붙여넣기")
        
        self.button_layout.addWidget(self.browse_button)
        self.button_layout.addWidget(self.paste_button)
        
        self.layout.addWidget(self.url_input)
        self.layout.addLayout(self.button_layout)
        
        # 드래그앤드롭 설정
        self.setAcceptDrops(True)
        self.url_input.setAcceptDrops(False)  # QLineEdit의 기본 드래그앤드롭 비활성화
        
        # 시그널 연결
        self.browse_button.clicked.connect(self.browse_image)
        self.paste_button.clicked.connect(self.paste_image)
        
        # 이미지 업로드를 위한 준비
        self.temp_dir = tempfile.gettempdir()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 이벤트 처리"""
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasImage():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """드롭 이벤트 처리"""
        mime_data = event.mimeData()
        
        if mime_data.hasUrls():
            url = mime_data.urls()[0]
            file_path = url.toLocalFile()
            
            # 이미지 파일인지 확인
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image'):
                self.upload_image(file_path)
            else:
                QMessageBox.warning(self, "파일 형식 오류", "이미지 파일만 사용할 수 있습니다.")
        
        elif mime_data.hasImage():
            # 이미지 데이터를 임시 파일로 저장
            image = mime_data.imageData()
            temp_path = os.path.join(self.temp_dir, f"temp_image_{uuid.uuid4()}.png")
            image.save(temp_path, "PNG")
            self.upload_image(temp_path)
    
    def browse_image(self):
        """이미지 파일 선택 대화상자 표시"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 파일 선택", "", "이미지 파일 (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_path:
            self.upload_image(file_path)
    
    def paste_image(self):
        """클립보드에서 이미지 붙여넣기"""
        try:
            image = ImageGrab.grabclipboard()
            
            if image and isinstance(image, Image.Image):
                # 이미지를 임시 파일로 저장
                temp_path = os.path.join(self.temp_dir, f"clipboard_image_{uuid.uuid4()}.png")
                image.save(temp_path)
                self.upload_image(temp_path)
            else:
                QMessageBox.warning(self, "클립보드 오류", "클립보드에 이미지가 없습니다.")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"이미지 붙여넣기 중 오류 발생: {str(e)}")
    
    def upload_image(self, file_path):
        """이미지를 구글 드라이브에 업로드하고 URL 반환"""
        try:
            # UI 상태 업데이트
            self.url_input.setText("이미지를 업로드하는 중...")
            QApplication.processEvents()
            
            # 구글 드라이브 API 인증
            creds = get_credentials()
            drive_service = build('drive', 'v3', credentials=creds)
            
            # 파일 메타데이터 설정
            file_metadata = {
                'name': os.path.basename(file_path),
                'mimeType': mimetypes.guess_type(file_path)[0]
            }
            
            # 미디어 업로드 준비
            media = MediaFileUpload(file_path, mimetype=mimetypes.guess_type(file_path)[0])
            
            # 파일 업로드
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # 파일 공개 접근 권한 설정
            drive_service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            # 파일 URL 생성
            file_id = file.get('id')
            image_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            
            # 텍스트 필드에 URL 설정
            self.url_input.setText(image_url)
            
            # 임시 파일 정리
            if self.temp_dir in file_path:
                try:
                    os.remove(file_path)
                except:
                    pass
                
            return image_url
            
        except Exception as e:
            self.url_input.setText("")
            QMessageBox.warning(self, "업로드 오류", f"이미지 업로드 중 오류 발생: {str(e)}")
            return None
    
    def get_url(self):
        """현재 URL 반환"""
        return self.url_input.text().strip()
    
    def set_url(self, url):
        """URL 설정"""
        self.url_input.setText(url) 