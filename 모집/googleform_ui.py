import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QComboBox, QLineEdit, QFormLayout, QGroupBox, QRadioButton,
                           QMessageBox, QFileDialog, QApplication, QTextEdit, QListWidget, QInputDialog, QDialog)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent

import mimetypes
import tempfile
import uuid
from PIL import ImageGrab, Image
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build

# 현재 디렉토리 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 모듈 임포트
from auth import get_credentials
from template_loader import list_templates
from googleform import create_form_with_gui

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

class ProductOptionWidget(QWidget):
    """상품 옵션을 관리하는 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 상품 옵션 목록
        options_group = QGroupBox("희망상품 옵션")
        options_layout = QVBoxLayout()
        
        # 옵션 리스트
        self.options_list = QListWidget()
        self.options_list.setFixedHeight(100)  # 최소 높이에서 고정 높이로 변경
        
        # 버튼 영역
        buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("옵션 추가")
        self.edit_btn = QPushButton("옵션 편집")
        self.remove_btn = QPushButton("옵션 삭제")
        
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.remove_btn)
        
        options_layout.addWidget(self.options_list)
        options_layout.addLayout(buttons_layout)
        
        options_group.setLayout(options_layout)
        self.layout.addWidget(options_group)
        
        # 신호 연결
        self.add_btn.clicked.connect(self.add_option)
        self.edit_btn.clicked.connect(self.edit_option)
        self.remove_btn.clicked.connect(self.remove_option)
        
        # 내부 데이터 저장용 (label, image URL 쌍)
        self.option_data = []
        
        # 샘플 옵션 추가
        self.add_sample_options()
    
    def add_sample_options(self):
        """샘플 옵션 추가"""
        self.add_option_data("상품 1", "")
        self.add_option_data("상품 2", "")
        self.add_option_data("상품 3", "")
    
    def add_option_data(self, label, image_url=""):
        """옵션 데이터 추가 및 리스트 업데이트"""
        self.option_data.append({"label": label, "image": image_url})
        self.update_options_list()
    
    def update_option_data(self, index, label, image_url=""):
        """옵션 데이터 업데이트"""
        if 0 <= index < len(self.option_data):
            self.option_data[index] = {"label": label, "image": image_url}
            self.update_options_list()
    
    def update_options_list(self):
        """데이터에 맞게 리스트 위젯 업데이트"""
        self.options_list.clear()
        for option in self.option_data:
            display_text = option["label"]
            if option["image"]:
                display_text += " (이미지 있음)"
            self.options_list.addItem(display_text)
    
    def add_option(self):
        """새 옵션 추가"""
        # 옵션 추가 다이얼로그 생성
        dialog = OptionEditDialog(self)
        result = dialog.exec_()
        
        if result == OptionEditDialog.Accepted:
            label, image_url = dialog.get_option_data()
            if label:  # 라벨은 반드시 있어야 함
                self.add_option_data(label, image_url)
    
    def edit_option(self):
        """선택한 옵션 편집"""
        selected_row = self.options_list.currentRow()
        
        if selected_row >= 0 and selected_row < len(self.option_data):
            current_data = self.option_data[selected_row]
            
            # 옵션 편집 다이얼로그 생성
            dialog = OptionEditDialog(self, current_data["label"], current_data["image"])
            result = dialog.exec_()
            
            if result == OptionEditDialog.Accepted:
                label, image_url = dialog.get_option_data()
                if label:  # 라벨은 반드시 있어야 함
                    self.update_option_data(selected_row, label, image_url)
    
    def remove_option(self):
        """선택한 옵션 삭제"""
        selected_row = self.options_list.currentRow()
        
        if selected_row >= 0:
            reply = QMessageBox.question(
                self, "옵션 삭제", "선택한 옵션을 삭제하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.option_data.pop(selected_row)
                self.update_options_list()
    
    def get_options(self):
        """현재 모든 옵션 반환"""
        return self.option_data

class OptionEditDialog(QDialog):
    """상품 옵션 추가/편집을 위한 다이얼로그"""
    
    def __init__(self, parent=None, label="", image_url=""):
        super().__init__(parent)
        self.setWindowTitle("상품 옵션 편집")
        self.setMinimumWidth(500)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        
        # 상품명 입력
        form_layout = QFormLayout()
        self.label_input = QLineEdit(label)
        form_layout.addRow("상품명:", self.label_input)
        layout.addLayout(form_layout)
        
        # 이미지 업로드 위젯
        layout.addWidget(QLabel("상품 이미지:"))
        self.image_widget = ImageDropWidget()
        if image_url:
            self.image_widget.set_url(image_url)
        layout.addWidget(self.image_widget)
        
        # 버튼
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("취소")
        self.save_button = QPushButton("저장")
        self.save_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        # 시그널 연결
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.accept)
    
    def get_option_data(self):
        """입력된 옵션 데이터 반환"""
        return (self.label_input.text().strip(), 
                self.image_widget.get_url())

class GoogleFormUI(QWidget):
    """구글폼 만들기 UI 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)  # 기본 간격 20에서 10으로 줄임
        self.main_layout.setContentsMargins(20, 20, 20, 20)  # 여백 설정
        
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
            # '모집'이 포함된 템플릿만 필터링
            recruitment_templates = [template for template in templates if '모집' in template]
            if recruitment_templates:
                self.template_combo.addItems(recruitment_templates)
            else:
                self.template_combo.addItem("모집 관련 템플릿 없음")
        else:
            self.template_combo.addItem("사용 가능한 템플릿 없음")
        
        template_layout.addRow("템플릿:", self.template_combo)
        template_group.setLayout(template_layout)
        top_layout.addWidget(template_group)
        
        # 수평 레이아웃을 메인 레이아웃에 추가
        self.main_layout.addLayout(top_layout)
        
        # 섹션 간 간격 추가 - 간격 15에서 8로 줄임
        spacer1 = QWidget()
        spacer1.setFixedHeight(8)
        self.main_layout.addWidget(spacer1)
        
        # AI 생성하기 섹션 추가
        ai_group = QGroupBox("AI 생성하기")
        ai_layout = QHBoxLayout()
        ai_layout.setSpacing(12)  # 간격 설정
        ai_layout.setContentsMargins(15, 15, 15, 15)  # 여백 설정
        
        # AI 프롬프트 입력 텍스트 영역
        self.ai_prompt_input = QTextEdit()
        self.ai_prompt_input.setMinimumHeight(80)  # 높이 설정
        self.ai_prompt_input.setPlaceholderText("AI에게 폼 내용을 생성해달라고 요청해보세요. 예: '인스타그램 리뷰어 모집을 위한 폼을 만들어줘'")
        
        # AI 생성 버튼
        self.ai_generate_button = QPushButton("AI로 내용 생성하기")
        self.ai_generate_button.setFixedHeight(80)  # 버튼 높이 조정 (TextEdit와 동일하게)
        self.ai_generate_button.setFixedWidth(150)  # 버튼 너비 설정
        self.ai_generate_button.setStyleSheet("font-size: 13px;")
        
        ai_layout.addWidget(self.ai_prompt_input, 3)  # 가중치 3 (더 넓게)
        ai_layout.addWidget(self.ai_generate_button, 1)  # 가중치 1 (더 좁게)
        
        ai_group.setLayout(ai_layout)
        self.main_layout.addWidget(ai_group)
        
        # AI 생성과 폼 정보 사이 간격 추가 - 간격 15에서 8로 줄임
        spacer1_5 = QWidget()
        spacer1_5.setFixedHeight(8)
        self.main_layout.addWidget(spacer1_5)
        
        # 폴더명 및 폼 정보 입력 UI
        info_group = QGroupBox("폼 정보")
        info_layout = QFormLayout()
        info_layout.setSpacing(12)  # 폼 레이아웃 간격 설정
        info_layout.setContentsMargins(15, 15, 15, 15)  # 여백 설정
        
        self.folder_input = QLineEdit()
        self.title_input = QLineEdit()
        # 플레이스홀더 제거
        # self.title_input.setPlaceholderText("[팔도] 볼케이노 까르보나라 체험단 모집(블로그)")
        
        # 제목 입력을 위한 예시 라벨 추가
        title_example_widget = QWidget()
        title_example_layout = QVBoxLayout(title_example_widget)
        title_example_layout.setContentsMargins(0, 0, 0, 0)
        title_example_layout.setSpacing(2)
        
        title_example_label = QLabel("예 : [팔도] ooo 체험단 모집(블로그)")
        title_example_label.setStyleSheet("color: #666; font-size: 11px;")
        title_example_layout.addWidget(self.title_input)
        title_example_layout.addWidget(title_example_label)
        
        # QLineEdit 대신 QTextEdit 사용
        self.desc_input = QTextEdit()
        self.desc_input.setMinimumHeight(80)  # 높이 설정
        self.desc_input.setAcceptRichText(False)  # 서식 없는 텍스트만 허용
        
        # 이미지 입력 위젯을 커스텀 위젯으로 교체
        self.image_input_widget = ImageDropWidget()
        
        info_layout.addRow("생성할 구글폴더명:", self.folder_input)
        info_layout.addRow("폼 제목 (필수):", title_example_widget)
        info_layout.addRow("폼 설명 (필수):", self.desc_input)
        info_layout.addRow("이미지:", self.image_input_widget)
        
        info_group.setLayout(info_layout)
        self.main_layout.addWidget(info_group)
        
        # 상품 옵션과 채널 옵션을 가로로 배치하기 위한 레이아웃
        options_layout = QHBoxLayout()
        
        # 상품 옵션 위젯 
        self.product_options_widget = ProductOptionWidget()
        options_layout.addWidget(self.product_options_widget)
        
        # 상품 옵션과 비슷한 방식으로 채널 옵션 위젯 생성
        self.channel_options_group = QGroupBox("신청 채널 옵션")
        self.channel_options_layout = QVBoxLayout(self.channel_options_group)

        # 채널 옵션 목록
        self.channel_options_list = QListWidget()
        self.channel_options_list.setFixedHeight(100)  # 최소 높이에서 고정 높이로 변경

        # 기본 채널 옵션 추가
        default_channels = ["블로그", "인스타", "인스타-릴스", "유튜브"]
        for channel in default_channels:
            self.channel_options_list.addItem(channel)

        # 버튼 레이아웃
        self.channel_buttons_layout = QHBoxLayout()

        # 버튼들 추가
        self.add_channel_button = QPushButton("추가")
        self.edit_channel_button = QPushButton("편집")
        self.remove_channel_button = QPushButton("삭제")

        self.channel_buttons_layout.addWidget(self.add_channel_button)
        self.channel_buttons_layout.addWidget(self.edit_channel_button)
        self.channel_buttons_layout.addWidget(self.remove_channel_button)

        # 레이아웃에 추가
        # self.channel_options_layout.addWidget(QLabel("신청 채널 목록:"))
        self.channel_options_layout.addWidget(self.channel_options_list)
        self.channel_options_layout.addLayout(self.channel_buttons_layout)

        # 버튼 이벤트 연결
        self.add_channel_button.clicked.connect(self.add_channel_option)
        self.edit_channel_button.clicked.connect(self.edit_channel_option)
        self.remove_channel_button.clicked.connect(self.remove_channel_option)
        
        # 채널 옵션을 가로 레이아웃에 추가
        options_layout.addWidget(self.channel_options_group)
        
        # 가로 레이아웃을 메인 레이아웃에 추가
        self.main_layout.addLayout(options_layout)
        
        # 섹션 간 간격 추가 - 간격 15에서 8로 줄임
        spacer2 = QWidget()
        spacer2.setFixedHeight(8)
        self.main_layout.addWidget(spacer2)
        
        # 생성 버튼
        self.create_button = QPushButton("폼 생성하기")
        self.create_button.setFixedHeight(40)  # 버튼 높이 설정
        self.create_button.setStyleSheet("font-size: 14px;")  # 버튼 텍스트 크기 키우기
        self.create_button.clicked.connect(self.create_form)
        self.main_layout.addWidget(self.create_button)
        
        # 섹션 간 간격 추가 - 간격 15에서 8로 줄임
        spacer3 = QWidget()
        spacer3.setFixedHeight(8)
        self.main_layout.addWidget(spacer3)
        
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
        self.form_link_button = QPushButton("폼 수정하기")
        self.folder_link_button = QPushButton("폴더 열기")
        self.form_link_button.setVisible(False)
        self.folder_link_button.setVisible(False)
        
        self.link_buttons_layout.addWidget(self.form_link_button)
        self.link_buttons_layout.addWidget(self.folder_link_button)
        result_layout.addLayout(self.link_buttons_layout)
        
        result_group.setLayout(result_layout)
        self.main_layout.addWidget(result_group)
        
        self.main_layout.addStretch()
        
        # 라디오 버튼 변경 시 템플릿 콤보박스 활성화/비활성화
        self.radio_template.toggled.connect(self.toggle_form_options)
        self.radio_sample.toggled.connect(self.toggle_form_options)
        
    def toggle_form_options(self):
        """폼 생성 방식에 따라 UI 요소 활성화/비활성화"""
        is_template = self.radio_template.isChecked()
        self.template_combo.setEnabled(is_template)
    
    def create_form(self):
        """폼 생성 버튼 클릭 시 처리"""
        # 입력값 검증
        folder_name = self.folder_input.text().strip()
        title = self.title_input.text().strip()
        description = self.desc_input.toPlainText().strip()
        image_url = self.image_input_widget.get_url()
        
        # 상품 옵션 가져오기
        product_options = self.product_options_widget.get_options()
        
        # 채널 옵션 가져오기
        channel_options = []
        for i in range(self.channel_options_list.count()):
            channel = self.channel_options_list.item(i).text()
            channel_options.append(channel)
        
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
        
        # 생성 전 확인 대화상자 표시
        # 상품 옵션 정보 포맷팅
        product_options_text = "\n".join([f"- {option['label']}" + (f" (이미지 있음)" if option['image'] else "") 
                                       for option in product_options])

        # 채널 옵션 정보 포맷팅
        channel_options_text = ", ".join(channel_options)

        confirm = QMessageBox.question(
            self,
            "폼 생성 확인",
            f"다음 정보로 구글폼을 생성하시겠습니까?\n\n"
            f"폴더명: {folder_name}\n"
            f"폼 제목: {title}\n\n"
            f"희망상품 옵션:\n{product_options_text}\n\n"
            f"신청 채널: {channel_options_text}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        # 사용자가 확인을 선택하지 않으면 취소
        if confirm != QMessageBox.Yes:
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
            image_url if image_url else None,
            product_options,
            channel_options
        )
        
        # 결과 표시
        if result['success']:
            self.result_label.setText(result['message'])
            QMessageBox.information(self, "성공", "폼이 성공적으로 생성되었습니다!")
            
            # 폼 편집 URL 버튼 설정
            self.form_link_button.setVisible(True)
            self.form_link_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(result['form_edit_url']))
            )
            
            # 링크 버튼 추가
            self.form_view_button = QPushButton("공유 링크 열기")
            self.link_buttons_layout.addWidget(self.form_view_button)
            self.form_view_button.setVisible(True)
            self.form_view_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(result['form_view_url']))
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
    
    def add_channel_option(self):
        """신청 채널 옵션 추가"""
        channel, ok = QInputDialog.getText(self, "채널 추가", "새 채널 이름:")
        if ok and channel:
            self.channel_options_list.addItem(channel)
    
    def edit_channel_option(self):
        """선택된 채널 옵션 편집"""
        current_item = self.channel_options_list.currentItem()
        if current_item:
            old_text = current_item.text()
            new_text, ok = QInputDialog.getText(self, "채널 편집", "채널 이름:", text=old_text)
            if ok and new_text:
                current_item.setText(new_text)
    
    def remove_channel_option(self):
        """선택된 채널 옵션 삭제"""
        current_row = self.channel_options_list.currentRow()
        if current_row >= 0:
            # 확인 대화상자 없이 바로 삭제
            self.channel_options_list.takeItem(current_row)
    
    def get_form_data(self):
        """폼 데이터 수집"""
        # ... 기존 코드 ...
        
        # 채널 옵션 수집
        channel_options = []
        for i in range(self.channel_options_list.count()):
            channel = self.channel_options_list.item(i).text()
            channel_options.append(channel)
        
        return {
            # ... 기존 데이터 ...
            'custom_channel_options': channel_options if channel_options else None
        }
    
    def submit_form(self):
        """폼 제출 처리"""
        form_data = self.get_form_data()
        
        # ... 기존 코드 ...
        
        result = create_form_with_gui(
            template_name=form_data['template_name'],
            folder_name=form_data['folder_name'],
            custom_title=form_data['custom_title'],
            custom_description=form_data['custom_description'],
            custom_image_url=form_data['custom_image_url'],
            custom_product_options=form_data['custom_product_options'],
            custom_channel_options=form_data['custom_channel_options']  # 채널 옵션 추가
        )
        
        # ... 기존 코드 계속 ... 