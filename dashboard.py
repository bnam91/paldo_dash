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
                             QMessageBox, QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent

# 모집 폴더에서 필요한 모듈 임포트
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '모집'))
from template_loader import list_templates
from googleform import create_form_with_gui

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
        self.initUI()
        
    def initUI(self):
        # 메인 위젯과 레이아웃 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 탭 위젯 생성
        self.tabs = QTabWidget()
        
        # 각 탭 생성
        self.recruitment_tab = self.create_tab_with_sidebar("모집")
        self.selection_tab = self.create_tab_with_sidebar("선정")
        self.report_tab = self.create_tab_with_sidebar("보고")
        
        # 모집 탭에 사이드바 아이템 추가
        self.add_sidebar_items(self.recruitment_tab, ["구글폼 만들기", "노션 가이드만들기", "배포"])
        
        # 탭 추가
        self.tabs.addTab(self.recruitment_tab["widget"], "모집")
        self.tabs.addTab(self.selection_tab["widget"], "선정")
        self.tabs.addTab(self.report_tab["widget"], "보고")
        
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
        form_widget = QWidget()
        main_layout = QVBoxLayout(form_widget)
        main_layout.setSpacing(20)  # 기본 간격 설정
        main_layout.setContentsMargins(20, 20, 20, 20)  # 여백 설정
        
        # 폼 생성 방식과 템플릿 선택을 수평으로 배치
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)  # 수평 레이아웃 간격 설정
        
        # 폼 생성 방식 선택 그룹
        method_group = QGroupBox("폼 생성 방식")
        method_layout = QVBoxLayout()
        method_layout.setSpacing(10)  # 그룹 내 간격 설정
        method_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내 여백 설정
        
        self.radio_template = QRadioButton("템플릿 사용하여 생성")
        self.radio_sample = QRadioButton("기본 샘플 폼 생성")
        self.radio_template.setChecked(True)  # 기본값으로 템플릿 선택
        
        method_layout.addWidget(self.radio_template)
        method_layout.addWidget(self.radio_sample)
        method_group.setLayout(method_layout)
        top_layout.addWidget(method_group)
        
        # 템플릿 선택 UI
        template_group = QGroupBox("템플릿 선택")
        template_layout = QFormLayout()
        
        self.template_combo = QComboBox()
        
        # 사용 가능한 템플릿 목록 가져오기
        templates = list_templates()
        if templates:
            self.template_combo.addItems(templates)
        else:
            self.template_combo.addItem("사용 가능한 템플릿 없음")
        
        template_layout.addRow("템플릿:", self.template_combo)
        template_group.setLayout(template_layout)
        top_layout.addWidget(template_group)
        
        # 수평 레이아웃을 메인 레이아웃에 추가
        main_layout.addLayout(top_layout)
        
        # 섹션 간 간격 추가
        spacer1 = QWidget()
        spacer1.setFixedHeight(15)
        main_layout.addWidget(spacer1)
        
        # 폴더명 및 폼 정보 입력 UI
        info_group = QGroupBox("폼 정보")
        info_layout = QFormLayout()
        info_layout.setSpacing(12)  # 폼 레이아웃 간격 설정
        info_layout.setContentsMargins(15, 15, 15, 15)  # 여백 설정
        
        self.folder_input = QLineEdit()
        self.title_input = QLineEdit()
        self.desc_input = QLineEdit()
        
        # 이미지 입력 위젯을 커스텀 위젯으로 교체
        self.image_input_widget = ImageDropWidget()
        
        info_layout.addRow("생성할 구글폴더명:", self.folder_input)
        info_layout.addRow("폼 제목 (필수):", self.title_input)
        info_layout.addRow("폼 설명 (필수):", self.desc_input)
        info_layout.addRow("이미지:", self.image_input_widget)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # 섹션 간 간격 추가
        spacer2 = QWidget()
        spacer2.setFixedHeight(15)
        main_layout.addWidget(spacer2)
        
        # 생성 버튼
        self.create_button = QPushButton("폼 생성하기")
        self.create_button.setFixedHeight(40)  # 버튼 높이 설정
        self.create_button.setStyleSheet("font-size: 14px;")  # 버튼 텍스트 크기 키우기
        self.create_button.clicked.connect(self.create_form)
        main_layout.addWidget(self.create_button)
        
        # 섹션 간 간격 추가
        spacer3 = QWidget()
        spacer3.setFixedHeight(15)
        main_layout.addWidget(spacer3)
        
        # 결과 표시 부분
        result_group = QGroupBox("생성 결과")
        result_layout = QVBoxLayout()
        result_layout.setSpacing(12)  # 결과 영역 간격 설정
        result_layout.setContentsMargins(15, 15, 15, 15)  # 여백 설정
        
        # 결과 텍스트 레이블
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        result_layout.addWidget(self.result_label)
        
        # 링크 버튼 영역
        self.link_buttons_layout = QHBoxLayout()
        
        # 초기 상태에서는 버튼을 숨김
        self.form_link_button = QPushButton("폼 열기")
        self.folder_link_button = QPushButton("폴더 열기")
        self.form_link_button.setVisible(False)
        self.folder_link_button.setVisible(False)
        
        self.link_buttons_layout.addWidget(self.form_link_button)
        self.link_buttons_layout.addWidget(self.folder_link_button)
        result_layout.addLayout(self.link_buttons_layout)
        
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)
        
        main_layout.addStretch()
        return form_widget
    
    def toggle_form_options(self):
        """폼 생성 방식에 따라 UI 요소 활성화/비활성화"""
        is_template = self.radio_template.isChecked()
        self.template_combo.setEnabled(is_template)
    
    def create_form(self):
        """폼 생성 버튼 클릭 시 처리"""
        # 입력값 검증
        folder_name = self.folder_input.text().strip()
        title = self.title_input.text().strip()
        description = self.desc_input.text().strip()
        image_url = self.image_input_widget.get_url()
        
        if not folder_name:
            QMessageBox.warning(self, "입력 오류", "저장할 폴더명을 입력해주세요.")
            return
        
        if not title:
            QMessageBox.warning(self, "입력 오류", "폼 제목을 입력해주세요.")
            return
        
        if not description:
            QMessageBox.warning(self, "입력 오류", "폼 설명을 입력해주세요.")
            return
        
        # 템플릿 또는 샘플 선택
        template_name = None
        if self.radio_template.isChecked():
            template_name = self.template_combo.currentText()
            if template_name == "사용 가능한 템플릿 없음":
                QMessageBox.warning(self, "템플릿 오류", "사용 가능한 템플릿이 없습니다.")
                return
        
        # "처리 중" 메시지 표시
        self.result_label.setText("폼을 생성하는 중입니다. 잠시만 기다려주세요...")
        self.form_link_button.setVisible(False)
        self.folder_link_button.setVisible(False)
        QApplication.processEvents()  # UI 업데이트
        
        # 폼 생성 함수 호출
        result = create_form_with_gui(
            template_name, 
            folder_name, 
            title, 
            description, 
            image_url if image_url else None
        )
        
        # 결과 표시
        if result['success']:
            self.result_label.setText(result['message'])
            QMessageBox.information(self, "성공", "폼이 성공적으로 생성되었습니다!")
            
            # 폼 URL 버튼 설정
            self.form_link_button.setVisible(True)
            self.form_link_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(result['form_url']))
            )
            
            # 폴더 URL 버튼 설정
            folder_url = f"https://drive.google.com/drive/folders/{result['folder_id']}"
            self.folder_link_button.setVisible(True)
            self.folder_link_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(folder_url))
            )
        else:
            self.result_label.setText(result['message'])
            QMessageBox.warning(self, "오류", result['message'])
    
    def run_googleform(self):
        """구글폼 만들기 스크립트 실행"""
        # 이 함수는 더 이상 사용하지 않지만, 호환성을 위해 남겨둠
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '모집', 'googleform.py')
            subprocess.Popen([sys.executable, script_path])
            print("구글폼 만들기 스크립트가 실행되었습니다.")
        except Exception as e:
            print(f"구글폼 만들기 스크립트 실행 중 오류 발생: {e}")

