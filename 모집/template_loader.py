import json
import os

def load_template(template_name):
    """
    템플릿 파일을 로드하여 폼 생성에 필요한 데이터를 반환합니다.
    
    Args:
        template_name (str): 템플릿 이름(확장자 제외)
    
    Returns:
        dict: 템플릿 데이터
    """
    # 절대 경로 사용으로 수정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, 'templates', f'{template_name}.json')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        return template_data
    except FileNotFoundError:
        print(f"오류: '{template_name}' 템플릿을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print(f"오류: '{template_name}' 템플릿 파일 형식이 올바르지 않습니다.")
        return None

def list_templates():
    """
    사용 가능한 모든 템플릿 목록을 반환합니다.
    
    Returns:
        list: 템플릿 이름 목록
    """
    # 절대 경로 사용으로 수정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, 'templates')
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        return []
    
    template_files = [f[:-5] for f in os.listdir(templates_dir) 
                     if f.endswith('.json')]
    return template_files 