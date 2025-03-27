import sys
import os
from PyQt5.QtWidgets import QApplication
from dashboard import Dashboard
from release_updater import ReleaseUpdater
import PyQt5

if __name__ == "__main__":
    # Qt 플러그인 경로 설정
    qt_plugin_path = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path
    
    # GitHub 저장소 정보 설정
    owner = os.environ.get("GITHUB_OWNER", "bnam91")
    repo = os.environ.get("GITHUB_REPO", "paldo_dash")
    
    # 최신 버전 확인 및 업데이트
    try:
        updater = ReleaseUpdater(owner=owner, repo=repo)
        update_success = updater.update_to_latest()
        
        if update_success:
            print("최신 버전으로 업데이트되었거나 이미 최신 버전입니다.")
        else:
            print("업데이트 실패, 이전 버전으로 계속 진행합니다...")
    except Exception as e:
        print(f"버전 확인 중 오류 발생: {e}")
    
    # PyQt 애플리케이션 실행
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_()) 


