import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def get_local_ip() -> str:
    """Detecta la IP local de la computadora en la red Wi-Fi / LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def ensure_dependencies():
    """Verifica que las dependencias requeridas esten instaladas."""
    try:
        import fastapi
        import uvicorn
        import duckdb
    except ImportError:
        print("[AVISO] Dependencias faltantes detectadas. Instalando requirements.txt...")
        import subprocess
        req_file = Path(__file__).resolve().parent / "requirements.txt"
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])


def main():
    parser = argparse.ArgumentParser(description="Lanzador del Servidor CDR")
    parser.add_argument("--host", default=None, help="Host a enlazar (ej: 0.0.0.0 o 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Puerto del servidor (ej: 8000)")
    parser.add_argument("--browser", choices=["yes", "no", "ask"], default="yes", help="Abrir navegador automaticamente")
    parser.add_argument("--interactive", action="store_true", help="Forzar preguntas interactivas en consola")

    args = parser.parse_args()
    detected_ip = get_local_ip()

    host = args.host
    port = args.port
    open_browser = args.browser

    # Si se pide modo interactivo o no se especificaron host/puerto
    if args.interactive or host is None or port is None:
        print("=" * 72)
        print("                 SISTEMA DE GRAFICAS CDR - INICIO DE SERVIDOR")
        print("=" * 72)
        print(f"  Equipo:              {socket.gethostname()}")
        print(f"  IP detectada en Wi-Fi: {detected_ip}")
        print("=" * 72)
        print()
        print("  Seleccione el modo de conexion:")
        print("    [1] Red Local / Wi-Fi [RECOMENDADO] (0.0.0.0)")
        print("        - Permite ingresar desde esta PC y desde otras PCs en el Wi-Fi.")
        print("    [2] Solo esta PC [Localhost] (127.0.0.1)")
        print("        - Acceso exclusivo para esta misma computadora.")
        print()

        choice = input("  Elija una opcion [1/2] (Presione Enter para 1): ").strip()
        if choice == "2":
            host = "127.0.0.1"
        else:
            host = "0.0.0.0"

        port_input = input("  Ingrese el puerto del servidor (Presione Enter para 8000): ").strip()
        port = int(port_input) if port_input.isdigit() else 8000

        if open_browser == "ask":
            b_choice = input("  Desea abrir el navegador automaticamente? (S/N) [Por defecto: S]: ").strip().lower()
            open_browser = "no" if b_choice == "n" else "yes"

    if host is None:
        host = "0.0.0.0"
    if port is None:
        port = 8000

    ensure_dependencies()

    import uvicorn

    print()
    print("=" * 72)
    print("                         SERVIDOR CDR EN EJECUCION")
    print("=" * 72)
    print(f"  Host:   {host}")
    print(f"  Puerto: {port}")
    print("-" * 72)
    print("  ENLACES DE ACCESO:")
    print(f"    - Desde esta PC:                 http://localhost:{port}")
    print(f"    - Desde esta PC (IP local):      http://127.0.0.1:{port}")
    if detected_ip != "127.0.0.1":
        print(f"    - Desde OTRAS PCs en este Wi-Fi: http://{detected_ip}:{port}")
    print("-" * 72)
    print("  RECORDATORIO PARA OTRAS PCS:")
    print("  * Ambas computadoras deben estar conectadas a la MISMA red Wi-Fi.")
    print(f"  * Si otra PC no conecta, verifique el Firewall de Windows para el puerto {port}.")
    print("  * Para detener el servidor, presione Ctrl + C en esta ventana.")
    print("=" * 72)
    print()

    if open_browser == "yes":
        def _open():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open, daemon=True).start()

    # Ejecutar uvicorn apuntando a app.main:app
    backend_dir = str(Path(__file__).resolve().parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
