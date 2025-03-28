import os
import sys

# 상위 디렉토리를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from auth import get_credentials
from template_loader import load_template, list_templates

def create_form_from_template(template_name, folder_id, custom_title=None, custom_description=None, custom_image_url=None, custom_product_options=None, custom_channel_options=None):
    """템플릿을 기반으로 구글 폼을 생성합니다."""
    template_data = load_template(template_name)
    if not template_data:
        return None
    
    # 사용자 입력 값이 있으면 템플릿 데이터 대체
    if custom_title:
        template_data['title'] = custom_title
    if custom_description:
        template_data['description'] = custom_description
    if custom_image_url:
        template_data['image_url'] = custom_image_url
    
    # 사용자가 정의한 상품 옵션이 있는 경우 해당 질문 찾아서 업데이트
    if custom_product_options and len(custom_product_options) > 0:
        for i, question in enumerate(template_data['questions']):
            if "희망상품" in question.get('title', ''):
                template_data['questions'][i]['options'] = custom_product_options
                break
    
    # 사용자가 정의한 채널 옵션이 있는 경우 해당 질문 찾아서 업데이트
    if custom_channel_options and len(custom_channel_options) > 0:
        for i, question in enumerate(template_data['questions']):
            if "신청 채널" in question.get('title', ''):
                template_data['questions'][i]['options'] = custom_channel_options
                break
    
    try:
        # 인증 정보 가져오기
        creds = get_credentials()
        
        # Forms API 서비스 빌드
        forms_service = build('forms', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 새 폼 생성
        form = {
            'info': {
                'title': template_data['title'],
                'documentTitle': template_data['title']
            }
        }
        
        # Forms API 호출하여 폼 생성
        created_form = forms_service.forms().create(body=form).execute()
        form_id = created_form['formId']
        
        print(f"폼이 성공적으로 생성되었습니다. 폼 ID: {form_id}")
        
        # 폼 설명 업데이트
        if 'description' in template_data:
            update_form_settings = {
                'requests': [
                    {
                        'updateFormInfo': {
                            'info': {
                                'description': template_data['description']
                            },
                            'updateMask': 'description'
                        }
                    }
                ]
            }
            forms_service.forms().batchUpdate(formId=form_id, body=update_form_settings).execute()
        
        # 템플릿의 질문들 추가
        requests = []
        for index, question in enumerate(template_data['questions']):
            question_request = create_question_request(question, index)
            if question_request:
                requests.append(question_request)
        
        if requests:
            update_form = {'requests': requests}
            forms_service.forms().batchUpdate(formId=form_id, body=update_form).execute()
        
        # 이미지 추가 (템플릿에 이미지 URL이 있는 경우)
        if 'image_url' in template_data and template_data['image_url']:
            add_image_request = {
                'requests': [
                    {
                        'createItem': {
                            'item': {
                                'title': '',
                                'imageItem': {
                                    'image': {
                                        'sourceUri': template_data['image_url']
                                    }
                                }
                            },
                            'location': {'index': 0}  # 첫 번째 위치에 이미지 추가
                        }
                    }
                ]
            }
            forms_service.forms().batchUpdate(formId=form_id, body=add_image_request).execute()
        
        # 폼의 소유권 설정 및 지정된 폴더로 이동
        # 현재 파일의 상위 폴더 확인
        file = drive_service.files().get(
            fileId=form_id,
            fields='parents'
        ).execute()
        
        print(f"현재 폼의 부모 폴더: {file.get('parents', [])}")
        
        # 모든 부모 폴더를 쉼표로 구분된 문자열로 결합
        current_parents = ','.join(file.get('parents', []))
        
        # 파일 이동 (이전 부모 모두 제거, 새 부모 추가)
        updated_file = drive_service.files().update(
            fileId=form_id,
            addParents=folder_id,
            removeParents=current_parents,
            fields='id, parents, name',
        ).execute()
        
        print(f"폼이 성공적으로 폴더로 이동되었습니다. 파일명: {updated_file.get('name')}, 새 부모 폴더: {updated_file.get('parents')}")
        
        # 폼 생성 후 공유 가능 설정
        # 폼에 대한 접근 권한 설정 (링크가 있는 모든 사용자가 접근 가능하도록)
        drive_service.permissions().create(
            fileId=form_id,
            body={
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False
            }
        ).execute()
        
        print("폼이 '링크가 있는 모든 사용자'와 공유되도록 설정되었습니다.")
        
        # 편집 URL 및 제출용 URL 생성
        form_edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        form_view_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
        
        return {
            'form_id': form_id,
            'form_edit_url': form_edit_url,
            'form_view_url': form_view_url
        }
        
    except HttpError as error:
        print(f"오류가 발생했습니다: {error}")
        return None

def create_question_request(question, index):
    """템플릿 질문 데이터를 API 요청 형식으로 변환합니다."""
    request = {
        'createItem': {
            'item': {
                'title': question['title'],
                'questionItem': {
                    'question': {
                        'required': question.get('required', False)
                    }
                }
            },
            'location': {'index': index}
        }
    }
    
    # 질문 유형에 따른 설정
    if question['type'] == 'TEXT':
        request['createItem']['item']['questionItem']['question']['textQuestion'] = {}
    elif question['type'] == 'PARAGRAPH_TEXT':
        request['createItem']['item']['questionItem']['question']['textQuestion'] = {'paragraph': True}
    elif question['type'] == 'RADIO' or question['type'] == 'CHECKBOX':
        # 옵션 처리 - 간단한 문자열 또는 객체일 수 있음
        options = []
        seen_values = set()  # 중복 확인을 위한 집합
        
        for option in question.get('options', []):
            if isinstance(option, dict):
                value = option.get('label', '')
                # 중복된 값인지 확인
                if value in seen_values:
                    # 중복된 경우 고유 값으로 만들기 (숫자 추가)
                    original_value = value
                    counter = 1
                    while value in seen_values:
                        value = f"{original_value} ({counter})"
                        counter += 1
                
                seen_values.add(value)
                option_data = {'value': value}
                
                # 이미지 URL이 있으면 이미지 정보 추가
                if 'image' in option and option['image']:
                    option_data['image'] = {
                        'sourceUri': option['image']
                    }
                options.append(option_data)
            else:
                # 문자열 옵션인 경우
                value = str(option)
                if value in seen_values:
                    # 중복된 경우 고유 값으로 만들기 (숫자 추가)
                    original_value = value
                    counter = 1
                    while value in seen_values:
                        value = f"{original_value} ({counter})"
                        counter += 1
                
                seen_values.add(value)
                options.append({'value': value})
        
        request['createItem']['item']['questionItem']['question']['choiceQuestion'] = {
            'type': question['type'],
            'options': options
        }
    else:
        print(f"지원하지 않는 질문 유형: {question['type']}")
        return None
    
    return request

def create_sample_form(form_title, folder_id):
    """샘플 구글 폼을 생성하고 지정된 폴더에 저장합니다."""
    try:
        # 인증 정보 가져오기
        creds = get_credentials()
        
        # Forms API 서비스 빌드
        # 참고: Google Forms API는 v1 버전을 사용합니다
        forms_service = build('forms', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 새 폼 생성
        form = {
            'info': {
                'title': form_title,
                'documentTitle': form_title
            }
        }
        
        # Forms API 호출하여 폼 생성
        created_form = forms_service.forms().create(body=form).execute()
        form_id = created_form['formId']
        
        print(f"폼이 성공적으로 생성되었습니다. 폼 ID: {form_id}")
        
        # 폼에 질문 추가
        update_form = {
            'requests': [
                # 텍스트 질문 추가
                {
                    'createItem': {
                        'item': {
                            'title': '이름을 입력해주세요.',
                            'questionItem': {
                                'question': {
                                    'required': True,
                                    'textQuestion': {}
                                }
                            }
                        },
                        'location': {'index': 0}
                    }
                },
                # 라디오 버튼 질문 추가
                {
                    'createItem': {
                        'item': {
                            'title': '참가 가능한 날짜를 선택해주세요.',
                            'questionItem': {
                                'question': {
                                    'required': True,
                                    'choiceQuestion': {
                                        'type': 'RADIO',
                                        'options': [
                                            {'value': '5월 10일'},
                                            {'value': '5월 11일'},
                                            {'value': '5월 12일'},
                                            {'value': '5월 13일'}
                                        ]
                                    }
                                }
                            }
                        },
                        'location': {'index': 1}
                    }
                },
                # 체크박스 질문 추가
                {
                    'createItem': {
                        'item': {
                            'title': '참가하고 싶은 프로그램을 모두 선택해주세요.',
                            'questionItem': {
                                'question': {
                                    'required': True,
                                    'choiceQuestion': {
                                        'type': 'CHECKBOX',
                                        'options': [
                                            {'value': '워크샵'},
                                            {'value': '세미나'},
                                            {'value': '네트워킹'},
                                            {'value': '팀 프로젝트'}
                                        ]
                                    }
                                }
                            }
                        },
                        'location': {'index': 2}
                    }
                },
                # 긴 텍스트 질문 추가
                {
                    'createItem': {
                        'item': {
                            'title': '참가 동기를 자유롭게 작성해주세요.',
                            'questionItem': {
                                'question': {
                                    'required': False,
                                    'textQuestion': {
                                        'paragraph': True
                                    }
                                }
                            }
                        },
                        'location': {'index': 3}
                    }
                }
            ]
        }
        
        # Forms API 호출하여 질문 추가
        forms_service.forms().batchUpdate(formId=form_id, body=update_form).execute()
        
        # 폼의 소유권 설정 및 지정된 폴더로 이동
        # 먼저 현재 파일의 상위 폴더 확인
        file = drive_service.files().get(
            fileId=form_id,
            fields='parents'
        ).execute()
        
        print(f"현재 폼의 부모 폴더: {file.get('parents', [])}")
        
        # 모든 부모 폴더를 쉼표로 구분된 문자열로 결합
        current_parents = ','.join(file.get('parents', []))
        
        # 파일 이동 (이전 부모 모두 제거, 새 부모 추가)
        updated_file = drive_service.files().update(
            fileId=form_id,
            addParents=folder_id,
            removeParents=current_parents,
            fields='id, parents, name',
        ).execute()
        
        print(f"폼이 성공적으로 폴더로 이동되었습니다. 파일명: {updated_file.get('name')}, 새 부모 폴더: {updated_file.get('parents')}")
        
        # 폼 생성 후 공유 가능 설정
        # 폼에 대한 접근 권한 설정 (링크가 있는 모든 사용자가 접근 가능하도록)
        drive_service.permissions().create(
            fileId=form_id,
            body={
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False
            }
        ).execute()
        
        print("폼이 '링크가 있는 모든 사용자'와 공유되도록 설정되었습니다.")
        
        # 편집 URL 및 제출용 URL 생성
        form_edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        form_view_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
        
        return {
            'form_id': form_id,
            'form_edit_url': form_edit_url,
            'form_view_url': form_view_url
        }
        
    except HttpError as error:
        print(f"오류가 발생했습니다: {error}")
        return None

def create_form_with_gui(template_name, folder_name, custom_title, custom_description, custom_image_url=None, custom_product_options=None, custom_channel_options=None, target_drive_id="1J0-1mMfQYTkIO3jaI1OReBdPPTnXxP23"):
    """GUI에서 호출하는 폼 생성 함수"""
    try:
        # 인증 정보 가져오기
        creds = get_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 폴더 생성
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [target_drive_id]
        }
        
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        folder_id = folder.get('id')
        
        # 템플릿 기반 폼 생성
        if template_name:
            result = create_form_from_template(
                template_name, 
                folder_id, 
                custom_title, 
                custom_description, 
                custom_image_url,
                custom_product_options,
                custom_channel_options
            )
        else:
            result = create_sample_form(custom_title, folder_id)
        
        if result:
            return {
                'success': True,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'form_id': result['form_id'],
                'form_edit_url': result['form_edit_url'],
                'form_view_url': result['form_view_url'],
                'message': f"폼이 성공적으로 생성되었습니다! 편집 URL: {result['form_edit_url']}\n공유 URL: {result['form_view_url']}"
            }
        else:
            return {
                'success': False,
                'message': "폼 생성에 실패했습니다."
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f"오류가 발생했습니다: {str(e)}"
        }

def main():
    print("폼 생성 방식을 선택하세요:")
    print("1. 템플릿 사용하여 생성")
    print("2. 기본 샘플 폼 생성")
    
    choice = input("선택 (1 또는 2): ")
    
    # 지정된 드라이브 폴더 ID
    target_drive_id = "1J0-1mMfQYTkIO3jaI1OReBdPPTnXxP23"
    
    # 인증 정보 가져오기
    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    
    # 폴더 생성
    folder_name = input("저장할 폴더명을 입력하세요: ")
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [target_drive_id]
    }
    
    folder = drive_service.files().create(
        body=folder_metadata,
        fields='id'
    ).execute()
    
    folder_id = folder.get('id')
    print(f"폴더가 생성되었습니다. 폴더 ID: {folder_id}")
    
    result = None
    
    if choice == '1':
        templates = list_templates()
        
        if not templates:
            print("사용 가능한 템플릿이 없습니다.")
            return
        
        print("\n사용 가능한 템플릿:")
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template}")
        
        template_choice = input(f"템플릿 선택 (1-{len(templates)}): ")
        try:
            template_index = int(template_choice) - 1
            if 0 <= template_index < len(templates):
                selected_template = templates[template_index]
                
                # 사용자 정의 필드 입력 받기
                print("\n템플릿 정보를 입력해주세요:")
                
                # 폼 제목은 필수 입력 항목
                custom_title = ""
                while not custom_title.strip():
                    custom_title = input("폼 제목 (필수): ")
                    if not custom_title.strip():
                        print("폼 제목은 반드시 입력해야 합니다.")
                
                # 폼 설명은 필수 입력 항목
                custom_description = ""
                while not custom_description.strip():
                    custom_description = input("폼 설명 (필수): ")
                    if not custom_description.strip():
                        print("폼 설명은 반드시 입력해야 합니다.")
                
                # 이미지 URL은 선택 사항
                custom_image_url = input("이미지 URL (선택사항): ")
                if not custom_image_url.strip():
                    custom_image_url = None
                
                result = create_form_from_template(
                    selected_template, 
                    folder_id, 
                    custom_title, 
                    custom_description, 
                    custom_image_url
                )
            else:
                print("잘못된 선택입니다.")
                return
        except ValueError:
            print("숫자를 입력해주세요.")
            return
    else:
        form_title = input("생성할 폼의 제목을 입력하세요: ")
        result = create_sample_form(form_title, folder_id)
    
    if result:
        print(f"폼이 성공적으로 생성되었습니다!")
        print(f"편집 URL: {result['form_edit_url']}")
        print(f"공유 URL: {result['form_view_url']}")
    else:
        print("폼 생성에 실패했습니다.")

if __name__ == "__main__":
    main()
