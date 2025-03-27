'''
탭 기반 대시보드 UI
- 모집, 선정, 보고 탭
- 각 탭에 사이드바 구현
- 모집 탭에는 '구글폼 만들기', '노션 가이드만들기', '배포' 옵션
'''

import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QListWidget, QStackedWidget,
                             QListWidgetItem, QLabel, QPushButton, QComboBox,
                             QLineEdit, QFormLayout, QGroupBox, QRadioButton,
                             QMessageBox, QCheckBox, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent

# 모집 폴더에서 필요한 모듈 임포트
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '모집'))
from template_loader import list_templates
from googleform import create_form_with_gui
# 구글폼 UI 모듈 추가 임포트
from googleform_ui import GoogleFormUI

# 이미지 업로드를 위한 추가 임포트
import mimetypes
from googleapiclient.http import MediaFileUpload
from auth import get_credentials
from googleapiclient.discovery import build
import tempfile
import uuid
import os
from PIL import ImageGrab, Image

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

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("대시보드")
        self.setGeometry(100, 100, 1280, 800)
        self.admin_access_granted = False  # 관리자 접근 권한 초기화
        self.admin_tab_index = 7  # 관리자 탭의 인덱스 (나중에 설정됨)
        self.initUI()
        
    def initUI(self):
        # 메인 위젯과 레이아웃 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 탭 위젯 생성
        self.tabs = QTabWidget()
        
        # 각 탭 생성
        self.status_tab = self.create_tab_with_sidebar("전체현황")
        self.recruitment_tab = self.create_tab_with_sidebar("모집")
        self.selection_tab = self.create_tab_with_sidebar("선정")
        self.report_tab = self.create_tab_with_sidebar("보고")
        self.purchase_tab = self.create_tab_with_sidebar("가구매")
        self.empty_tab = self.create_tab_with_sidebar("-")  # 빈 탭 추가
        self.people_tab = self.create_tab_with_sidebar("인원정보")  # 인원정보 탭 추가
        self.admin_tab = self.create_tab_with_sidebar("관리자")  # 관리자 탭 추가
        
        # 현황 탭에 사이드바 아이템 추가
        self.add_sidebar_items(self.status_tab, ["대시보드", "통계"])
        
        # 모집 탭에 사이드바 아이템 추가
        self.add_sidebar_items(self.recruitment_tab, ["구글폼 만들기", "노션 가이드만들기", "배포", "인원선정"])
        
        # 인원정보 탭에 사이드바 아이템 추가
        self.add_sidebar_items(self.people_tab, ["전체 목록", "검색"])
        
        # 가구매 탭에 사이드바 아이템 추가
        self.add_sidebar_items(self.purchase_tab, ["구매내역", "등록"])
        
        # 관리자 탭에 사이드바 아이템 추가
        self.add_sidebar_items(self.admin_tab, ["사용자 관리", "시스템 설정", "로그 확인"])
        
        # 탭 추가 - 원하는 순서대로 배치
        self.tabs.addTab(self.status_tab["widget"], "전체현황")
        self.tabs.addTab(self.recruitment_tab["widget"], "모집")
        self.tabs.addTab(self.selection_tab["widget"], "선정")
        self.tabs.addTab(self.report_tab["widget"], "보고")
        self.tabs.addTab(self.purchase_tab["widget"], "가구매")
        self.tabs.addTab(self.empty_tab["widget"], "")  # 빈 탭 추가
        self.tabs.addTab(self.people_tab["widget"], "인원정보")  # 인원정보 탭 추가
        self.tabs.addTab(self.admin_tab["widget"], "관리자")
        
        # 관리자 탭 인덱스 저장 (이제 7번 인덱스)
        self.admin_tab_index = 7
        
        # 탭 변경 이벤트 연결
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # 관리자 탭에 초기 콘텐츠 설정 (인증 전)
        self.setup_admin_initial_content()
        
        main_layout.addWidget(self.tabs)
    
    def create_tab_with_sidebar(self, tab_name):
        # 탭 위젯 생성
        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        
        # 사이드바 위젯 생성
        sidebar = QListWidget()
        sidebar.setMaximumWidth(250)
        
        # 콘텐츠 스택 위젯 생성
        content_stack = QStackedWidget()
        
        # 레이아웃에 추가
        tab_layout.addWidget(sidebar)
        tab_layout.addWidget(content_stack)
        
        # 사이드바 아이템 선택 시 콘텐츠 변경 - 오프셋 1 적용
        sidebar.currentRowChanged.connect(lambda idx: content_stack.setCurrentIndex(idx + 1))
        
        return {"widget": tab_widget, "sidebar": sidebar, "content_stack": content_stack}
    
    def add_sidebar_items(self, tab_dict, items):
        sidebar = tab_dict["sidebar"]
        content_stack = tab_dict["content_stack"]
        
        # 먼저 기본 화면(아무것도 선택하지 않았을 때) 추가
        default_widget = QWidget()
        default_layout = QVBoxLayout(default_widget)
        default_label = QLabel("사이드바에서 항목을 선택하세요")
        default_label.setAlignment(Qt.AlignCenter)
        default_layout.addWidget(default_label)
        content_stack.addWidget(default_widget)
        
        # 사이드바에 아이템 추가
        for item_text in items:
            sidebar.addItem(item_text)
            
            # 각 아이템에 대한 콘텐츠 페이지 생성
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            
            # 콘텐츠 페이지 내용 추가
            if item_text == "구글폼 만들기":
                content_layout.addWidget(self.create_googleform_ui())
            else:
                label = QLabel(f"{item_text} 기능이 여기에 구현됩니다.")
                label.setAlignment(Qt.AlignCenter)
                button = QPushButton(item_text)
                content_layout.addWidget(label)
                content_layout.addWidget(button)
            
            content_layout.addStretch()
            
            # 콘텐츠 스택에 페이지 추가
            content_stack.addWidget(content_widget)
        
        # 초기 선택이 없으면 기본 화면 표시
        if sidebar.count() > 0:
            sidebar.setCurrentRow(0)  # 첫 번째 항목 선택
            content_stack.setCurrentIndex(1)  # 첫 번째 콘텐츠(인덱스 1)로 설정
        else:
            content_stack.setCurrentIndex(0)  # 기본 화면(인덱스 0) 표시
    
    def create_googleform_ui(self):
        """구글폼 만들기 UI 생성"""
        # 모듈화된 GoogleFormUI 위젯 반환
        return GoogleFormUI()
    
    def run_googleform(self):
        """구글폼 만들기 스크립트 실행"""
        # 이 함수는 더 이상 사용하지 않지만, 호환성을 위해 남겨둠
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '모집', 'googleform.py')
            subprocess.Popen([sys.executable, script_path])
            print("구글폼 만들기 스크립트가 실행되었습니다.")
        except Exception as e:
            print(f"구글폼 만들기 스크립트 실행 중 오류 발생: {e}")
    
    def setup_admin_initial_content(self):
        """관리자 탭의 초기 콘텐츠 설정 (인증 전)"""
        # 관리자 탭의 콘텐츠 스택에 새로운 위젯 추가 (인증 전 표시용)
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        
        # 인증 필요 메시지
        auth_label = QLabel("이 영역에 접근하려면 관리자 인증이 필요합니다.")
        auth_label.setAlignment(Qt.AlignCenter)
        auth_label.setStyleSheet("font-size: 16px; color: #666;")
        
        # 인증 버튼
        auth_button = QPushButton("관리자 인증하기")
        auth_button.setFixedWidth(200)
        auth_button.clicked.connect(self.authenticate_admin)
        
        auth_layout.addStretch()
        auth_layout.addWidget(auth_label)
        auth_layout.addSpacing(20)
        auth_layout.addWidget(auth_button, 0, Qt.AlignCenter)
        auth_layout.addStretch()
        
        # 관리자 탭의 콘텐츠 스택에 추가 (인덱스 0에)
        self.admin_tab["content_stack"].insertWidget(0, auth_widget)
        
        # 사이드바가 선택되었을 때 이벤트 처리를 위해 커스텀 처리
        self.admin_tab["sidebar"].currentRowChanged.disconnect()  # 기존 연결 해제
        self.admin_tab["sidebar"].currentRowChanged.connect(self.on_admin_sidebar_changed)
        
        # 초기 화면 설정 (인증 화면)
        self.admin_tab["content_stack"].setCurrentIndex(0)
        
        # 사이드바 비활성화
        self.admin_tab["sidebar"].setEnabled(False)
    
    def on_admin_sidebar_changed(self, index):
        """관리자 탭의 사이드바 아이템 선택 시 처리"""
        if self.admin_access_granted:
            # 인증이 성공한 경우에만 콘텐츠 변경 (인덱스 + 1 사용)
            self.admin_tab["content_stack"].setCurrentIndex(index + 1)
        else:
            # 인증이 안된 경우 인증 화면 유지
            self.admin_tab["content_stack"].setCurrentIndex(0)
    
    def authenticate_admin(self):
        """관리자 인증 처리"""
        password, ok = QInputDialog.getText(
            self, "관리자 인증", "승인번호를 입력하세요:", 
            QLineEdit.Password
        )
        
        # 비밀번호 확인
        if ok and password == "8422":
            self.admin_access_granted = True
            QMessageBox.information(self, "인증 성공", "관리자 모드에 접근합니다.")
            
            # 사이드바 활성화
            self.admin_tab["sidebar"].setEnabled(True)
            
            # 첫번째 사이드바 항목으로 이동
            if self.admin_tab["sidebar"].count() > 0:
                self.admin_tab["sidebar"].setCurrentRow(0)
                self.admin_tab["content_stack"].setCurrentIndex(1)  # 인덱스 1부터 실제 콘텐츠
        else:
            QMessageBox.warning(self, "인증 실패", "잘못된 승인번호입니다.")
    
    def on_tab_changed(self, index):
        """탭 변경 시 호출되는 이벤트 핸들러"""
        # 관리자 탭으로 이동하고 아직 인증되지 않았으면 인증 화면 표시
        if index == self.admin_tab_index and not self.admin_access_granted:
            # 인증 화면(인덱스 0)으로 설정
            self.admin_tab["content_stack"].setCurrentIndex(0)

