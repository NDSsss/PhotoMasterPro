import subprocess
import sys
import os

def start_server():
    """Запуск сервера FastAPI через uvicorn"""
    try:
        print("Запускаю ваш автоматический обработчик фотографий...")
        
        # Запускаем uvicorn напрямую
        cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
        
        # Запускаем сервер
        process = subprocess.Popen(cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 bufsize=1)
        
        print("Сервер запущен! Проверяю статус...")
        
        # Читаем первые несколько строк для проверки запуска
        for i, line in enumerate(process.stdout):
            print(line.strip())
            if i > 10:  # Показываем первые 10 строк лога
                break
                
        return process
        
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
        return None

if __name__ == "__main__":
    process = start_server()
    if process:
        print("\n✅ Ваш обработчик фотографий запущен успешно!")
        print("🌐 Откройте http://localhost:5000 для просмотра")
        
        try:
            # Ждем завершения процесса
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Остановка сервера...")
            process.terminate()