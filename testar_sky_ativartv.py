# -*- coding: utf-8 -*-
"""
=============================================================================
         TESTE INDEPENDENTE DE ATIVAÇÃO SKY+ (TV PAIRING) VIA NAVEGADOR
=============================================================================
Este script testa o novo fluxo solicitado:
1. Abre o navegador visível (headless=False)
2. Acessa https://www.skymais.com.br e efetua o login como Cliente SKY
3. Acessa https://www.skymais.com.br/ativar-tv
4. Digita o código de 6 dígitos da TV e confirma a ativação
5. Registra o resultado com logs detalhados e screenshot
=============================================================================
"""

import os
import sys
import time
import json
import re

# Força codificação UTF-8 no console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Cores ANSI
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

def banner():
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════════════════════╗
║                   TESTADOR DE ATIVAÇÃO SKY+ / SMART TV               ║
║           Fluxo: skymais.com.br -> Login SKY -> /ativar-tv           ║
╚══════════════════════════════════════════════════════════════════════╝{C.RESET}
""")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HITS_DIR = os.path.join(BASE_DIR, "hits")
SESSIONS_DIR = os.path.join(HITS_DIR, "browser_sessions")
SCREENSHOTS_DIR = os.path.join(HITS_DIR, "screenshots")
CONTAS_FILE = os.path.join(BASE_DIR, "skycontas.txt")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def sanitizar_nome(texto: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', texto.strip().lower())

def carregar_contas() -> list:
    contas = []
    if os.path.exists(CONTAS_FILE):
        try:
            with open(CONTAS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    linha = linha.strip()
                    if linha and ":" in linha and not linha.startswith("#"):
                        partes = linha.split(":", 1)
                        contas.append((partes[0].strip(), partes[1].strip()))
        except Exception as e:
            print(f"{C.YELLOW}[!] Aviso ao ler skycontas.txt: {e}{C.RESET}")
    return contas

def aplicar_stealth(page):
    """Proteções anti-automação."""
    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page)
    except Exception:
        pass
    try:
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = {
                app: { isInstalled: false },
                webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
                runtime: { PlatformOs: { WIN: 'win' } }
            };
        """)
    except Exception:
        pass

def fechar_cookies(page):
    try:
        cookie_btn = page.locator("button:has-text('Aceitar'), button:has-text('Concordar'), button:has-text('Entendi'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0 and cookie_btn.first.is_visible():
            cookie_btn.first.click(timeout=1000)
    except Exception:
        pass

def converter_audio_url_para_wav(page, audio_url: str):
    """Utiliza a Web Audio API do Chromium para converter MP3 para WAV sem ffmpeg."""
    js_decoder = """
    async (url) => {
        try {
            const resp = await fetch(url);
            const arrayBuffer = await resp.arrayBuffer();
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
            const numChannels = audioBuffer.numberOfChannels;
            const sampleRate = audioBuffer.sampleRate;
            const format = 1;
            const bitDepth = 16;
            
            const pcmData = audioBuffer.getChannelData(0);
            const byteRate = sampleRate * numChannels * (bitDepth / 8);
            const blockAlign = numChannels * (bitDepth / 8);
            const dataSize = pcmData.length * (bitDepth / 8);
            const wavBuffer = new ArrayBuffer(44 + dataSize);
            const view = new DataView(wavBuffer);
            
            function writeString(offset, string) {
                for (let i = 0; i < string.length; i++) {
                    view.setUint8(offset + i, string.charCodeAt(i));
                }
            }
            
            writeString(0, 'RIFF');
            view.setUint32(4, 36 + dataSize, true);
            writeString(8, 'WAVE');
            writeString(12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, format, true);
            view.setUint16(22, numChannels, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, byteRate, true);
            view.setUint16(32, numChannels * 2, true);
            view.setUint16(34, 16, true);
            writeString(36, 'data');
            view.setUint32(40, pcmData.length * 2, true);
            
            let offset = 44;
            for (let i = 0; i < pcmData.length; i++, offset += 2) {
                let s = Math.max(-1, Math.min(1, pcmData[i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
            
            let binary = '';
            const bytes = new Uint8Array(wavBuffer);
            const chunkSize = 0x8000;
            for (let i = 0; i < bytes.length; i += chunkSize) {
                binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
            }
            return btoa(binary);
        } catch(e) {
            return null;
        }
    }
    """
    try:
        wav_b64 = page.evaluate(js_decoder, audio_url)
        if wav_b64:
            import base64
            return base64.b64decode(wav_b64)
    except Exception:
        pass
    return None

def transcrever_audio_wav(wav_path: str):
    """Transcreve o áudio do reCAPTCHA automaticamente."""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)
        for lang in ["pt-BR", "en-US", "es-ES"]:
            try:
                text = r.recognize_google(audio, language=lang)
                if text and len(text.strip()) > 0:
                    return text.strip()
            except Exception:
                continue
    except Exception:
        pass
    return None

def resolver_recaptcha_se_existir(page, max_wait: int = 30) -> bool:
    """Resolve o reCAPTCHA 100% automaticamente via desafio de áudio."""
    import tempfile
    try:
        bframe = None
        for f in page.frames:
            if "recaptcha" in f.url and "bframe" in f.url:
                bframe = f
                break

        if not bframe:
            return True

        print(f"{C.YELLOW}[*] [reCAPTCHA] Desafio detectado! Tentando resolução 100% automática via áudio...{C.RESET}")
        
        # Clica no botão de áudio
        try:
            audio_btn = bframe.locator("#recaptcha-audio-button")
            if audio_btn.count() > 0 and audio_btn.first.is_visible():
                audio_btn.first.click(force=True, timeout=3000)
                time.sleep(1.5)
        except Exception:
            pass

        for rodada in range(1, 4):
            if "vrioservices" not in page.url.lower():
                print(f"{C.GREEN}[✓] [reCAPTCHA] Login concluído!{C.RESET}")
                return True

            audio_source = bframe.locator("#audio-source")
            if audio_source.count() == 0 or not audio_source.first.is_visible():
                try:
                    bframe.wait_for_selector("#audio-source", timeout=3000)
                except Exception:
                    pass
                audio_source = bframe.locator("#audio-source")

            if audio_source.count() > 0:
                audio_url = audio_source.get_attribute("src")
                if audio_url:
                    print(f"[*] [reCAPTCHA] Transcrevendo áudio de segurança (Rodada {rodada})...")
                    wav_bytes = converter_audio_url_para_wav(bframe, audio_url) or converter_audio_url_para_wav(page, audio_url)
                    if wav_bytes:
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                            tmp_wav.write(wav_bytes)
                            wav_file = tmp_wav.name
                        try:
                            texto_transcrito = transcrever_audio_wav(wav_file)
                        finally:
                            try:
                                os.remove(wav_file)
                            except Exception:
                                pass

                        if texto_transcrito:
                            resp_in = bframe.locator("#audio-response")
                            if resp_in.count() > 0:
                                resp_in.first.fill(texto_transcrito)
                                time.sleep(0.3)
                                verify_btn = bframe.locator("#recaptcha-verify-button")
                                if verify_btn.count() > 0:
                                    verify_btn.first.click(force=True)
                                    print(f"{C.GREEN}[✓] [reCAPTCHA] Resposta automática enviada: '{texto_transcrito}'{C.RESET}")
                                    time.sleep(1.8)
                                    return True

        # Fallback de espera se já estiver resolvido ou em transição
        for _ in range(max_wait):
            time.sleep(1)
            if "vrioservices" not in page.url.lower():
                print(f"{C.GREEN}[✓] [reCAPTCHA] Resolvido com sucesso!{C.RESET}")
                return True
            aberto = False
            for f in page.frames:
                if "recaptcha" in f.url and "bframe" in f.url:
                    try:
                        if f.locator("#rc-imageselect").is_visible() or f.locator(".rc-audiochallenge-control").is_visible():
                            aberto = True
                            break
                    except Exception:
                        pass
            if not aberto:
                print(f"{C.GREEN}[✓] [reCAPTCHA] Desafio finalizado!{C.RESET}")
                return True

    except Exception as e:
        print(f"{C.YELLOW}[!] [reCAPTCHA] Aviso: {e}{C.RESET}")
    return False

def executar_teste():
    banner()

    # 1. Verifica Playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"{C.RED}[ERRO] Playwright não está instalado.{C.RESET}")
        print(f"Execute: {C.WHITE}pip install playwright && playwright install chromium{C.RESET}")
        input("\nPressione ENTER para sair...")
        return

    # 2. Seleciona Conta (Automático)
    contas = carregar_contas()
    email_escolhido = ""
    senha_escolhida = ""

    # Se informado via argumentos: python testar_sky_ativartv.py <CODIGO> <EMAIL> <SENHA>
    if len(sys.argv) >= 4:
        codigo_tv = sys.argv[1].strip().upper()
        email_escolhido = sys.argv[2].strip()
        senha_escolhida = sys.argv[3].strip()
    elif len(sys.argv) == 2:
        codigo_tv = sys.argv[1].strip().upper()
        if contas:
            email_escolhido, senha_escolhida = contas[0]
    else:
        # Pergunta qual conta deseja usar
        padrao_email = "itacir@chiapetti.com.br"
        padrao_senha = "Chiapetti4822"
        if contas:
            padrao_email = contas[0][0]
            padrao_senha = contas[0][1]

        print(f"\n{C.WHITE}{C.BOLD}Configuração de Login Sky:{C.RESET}")
        user_in = input(f"Email, Telefone ou CPF SKY [Padrão: {padrao_email}]: ").strip()
        email_escolhido = user_in if user_in else padrao_email

        # Procura senha correspondente se for conta conhecida
        senha_sugerida = padrao_senha
        for em, sn in contas:
            if em.lower() == email_escolhido.lower():
                senha_sugerida = sn
                break
        
        # Procura em hits/raw_json/
        if email_escolhido != padrao_email or senha_sugerida == padrao_senha:
            sanit_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', email_escolhido.strip().lower())
            for possible_name in [sanit_name, email_escolhido.strip()]:
                raw_f = os.path.join(HITS_DIR, "raw_json", f"{possible_name}.json")
                if os.path.exists(raw_f):
                    try:
                        with open(raw_f, "r", encoding="utf-8") as rf:
                            d = json.load(rf)
                            if d.get("password"):
                                senha_sugerida = d.get("password")
                                break
                    except Exception:
                        pass

        pass_in = input(f"Senha Sky [Padrão: {senha_sugerida}]: ").strip()
        senha_escolhida = pass_in if pass_in else senha_sugerida

        codigo_tv = ""
        while len(codigo_tv) != 6 or not codigo_tv.isalnum():
            codigo_tv = input(f"\n{C.YELLOW}{C.BOLD}Digite o CÓDIGO DA SMART TV (6 dígitos):{C.RESET} ").strip().upper()

    headless_mode = "--headless" in sys.argv


    session_file = os.path.join(SESSIONS_DIR, f"{sanitizar_nome(email_escolhido)}.json")

    print(f"\n{C.GREEN}{C.BOLD}=== INICIANDO FLUXO DE ATIVAÇÃO ==={C.RESET}")
    print(f"1. Acessar https://www.skymais.com.br")
    print(f"2. Fazer Login como Cliente SKY")
    print(f"3. Acessar https://www.skymais.com.br/ativar-tv")
    print(f"4. Inserir código: {codigo_tv}")
    print("=" * 60)

    inicio = time.time()

    with sync_playwright() as p:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--window-size=1280,850",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        print(f"\n{C.CYAN}[*] Abrindo navegador Chromium...{C.RESET}")
        browser = p.chromium.launch(
            headless=headless_mode,
            args=args
        )

        storage_path = session_file if (os.path.exists(session_file) and os.path.getsize(session_file) > 100) else None
        if storage_path:
            print(f"{C.GREEN}[✓] Sessão pré-salva encontrada para {email_escolhido}. Carregando cookies/storage...{C.RESET}")

        context = browser.new_context(
            viewport={"width": 1280, "height": 850},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            storage_state=storage_path
        )

        page = context.new_page()
        page.set_default_timeout(35000)
        aplicar_stealth(page)

        # -------------------------------------------------------------
        # PASSO 1: ACESSAR https://www.skymais.com.br E FAZER LOGIN
        # -------------------------------------------------------------
        print(f"\n{C.CYAN}[PASSO 1] Acessando https://www.skymais.com.br ...{C.RESET}")
        page.goto("https://www.skymais.com.br", wait_until="domcontentloaded")
        time.sleep(2)
        fechar_cookies(page)

        # Verifica se já está logado
        ja_logado = False
        try:
            # Se encontrar avatar, perfil, ou não tiver botão de entrar
            if page.locator("button:has-text('Perfil'), img[alt*='avatar' i], [data-testid*='user-menu']").count() > 0:
                ja_logado = True
            # Checa se existe sessão no localStorage
            has_token = page.evaluate("() => !!(localStorage.getItem('sessionToken') || localStorage.getItem('profileToken'))")
            if has_token:
                ja_logado = True
        except Exception:
            pass

        if ja_logado:
            print(f"{C.GREEN}[✓] Usuário já se encontra logado na Sky+!{C.RESET}")
        else:
            print(f"{C.YELLOW}[*] Não está autenticado. Procurando botão de Login / Entrar...{C.RESET}")
            
            # Clica no botão Entrar da home
            entrar_clicado = False
            btn_login_selectors = [
                "button:has-text('Entrar')",
                "a:has-text('Entrar')",
                "button:has-text('Login')",
                "a:has-text('Login')",
                "button:has-text('Acessar')",
                "a:has-text('Acessar')",
                "[data-testid*='login' i]",
                "[data-testid*='entrar' i]"
            ]
            for sel in btn_login_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        print(f"[*] Clicando no botão '{sel}' na home...")
                        loc.first.click(timeout=3000)
                        entrar_clicado = True
                        time.sleep(2)
                        break
                except Exception:
                    pass

            # Procura a opção "Cliente SKY" ou botão [ SKY ]
            print(f"[*] Selecionando provedor [ SKY ]...")
            sky_selectors = [
                "//div[contains(., 'cliente SKY') or contains(., 'cliente sky')]//button[contains(., 'SKY') or contains(., 'Sky')]",
                "//div[contains(., 'cliente SKY') or contains(., 'cliente sky')]/following::button[1]",
                "button:has-text('SKY')",
                "button:has(img[alt*='SKY' i])",
                "a:has-text('SKY')",
                "a:has(img[alt*='SKY' i])",
                "button:text-is('SKY')",
                "[aria-label*='SKY' i]",
                "button.sky-button",
                "[data-testid*='sky' i]"
            ]
            for sel in sky_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        print(f"[*] Clicando na opção [ SKY ]...")
                        loc.first.click(timeout=3000)
                        time.sleep(2)
                        break
                except Exception:
                    pass

            # Preenche credenciais
            print(f"[*] Preenchendo login ({email_escolhido})...")
            user_selectors = [
                "input[name='username']",
                "input#username",
                "input[name='login']",
                "input#login",
                "input[name='email']",
                "input#email",
                "input[type='email']",
                "input[placeholder*='e-mail' i]",
                "input[placeholder*='cpf' i]",
                "input[type='text']"
            ]
            campo_usuario = None
            for sel in user_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        campo_usuario = loc.first
                        break
                except Exception:
                    pass

            if campo_usuario:
                campo_usuario.click()
                campo_usuario.fill(email_escolhido)
                campo_usuario.dispatch_event("input")
                campo_usuario.dispatch_event("change")
            else:
                print(f"{C.YELLOW}[!] Campo de usuário não encontrado automaticamente. Por favor, digite na tela se necessário.{C.RESET}")

            print(f"[*] Preenchendo senha...")
            pass_selectors = [
                "input[name='password']",
                "input#password",
                "input[name='senha']",
                "input#senha",
                "input[type='password']"
            ]
            campo_senha = None
            for sel in pass_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        campo_senha = loc.first
                        break
                except Exception:
                    pass

            if campo_senha:
                campo_senha.click()
                campo_senha.fill(senha_escolhida)
                campo_senha.dispatch_event("input")
                campo_senha.dispatch_event("change")
            else:
                print(f"{C.YELLOW}[!] Campo de senha não encontrado automaticamente.{C.RESET}")

            # Submete formulário
            btn_entrar = page.locator("button[type='submit'], button:has-text('Entrar'), button:has-text('Acessar')")
            if btn_entrar.count() > 0 and btn_entrar.first.is_visible():
                print(f"[*] Clicando em Entrar...")
                try:
                    btn_entrar.first.click(timeout=3000)
                except Exception:
                    pass
            elif campo_senha:
                campo_senha.press("Enter")

            # Trata reCAPTCHA se aparecer
            resolver_recaptcha_se_existir(page, max_wait=30)

            # Aguarda login concluir
            print(f"{C.CYAN}[*] Aguardando conclusão do login...{C.RESET}")
            for i in range(25):
                time.sleep(1)
                u = page.url.lower()
                if "vrioservices" not in u and "auth.sky" not in u and "login" not in u:
                    print(f"{C.GREEN}[✓] Login concluído com sucesso! URL atual: {page.url}{C.RESET}")
                    break
            
            # Salva sessão
            try:
                context.storage_state(path=session_file)
                print(f"{C.GREEN}[✓] Sessão salva em {session_file}{C.RESET}")
            except Exception:
                pass

        # -------------------------------------------------------------
        # PASSO 2: ACESSAR https://www.skymais.com.br/ativar-tv
        # -------------------------------------------------------------
        print(f"\n{C.CYAN}[PASSO 2] Navegando para https://www.skymais.com.br/ativar-tv ...{C.RESET}")
        page.goto("https://www.skymais.com.br/ativar-tv", wait_until="domcontentloaded")
        time.sleep(2)
        fechar_cookies(page)

        # Salva screenshot da tela de ativação
        tela_ativar_print = os.path.join(SCREENSHOTS_DIR, f"tela_ativar_{codigo_tv}.png")
        page.screenshot(path=tela_ativar_print)
        print(f"[*] Screenshot da tela salvo em: {tela_ativar_print}")

        # -------------------------------------------------------------
        # PASSO 3: INSERIR O CÓDIGO DA TV
        # -------------------------------------------------------------
        print(f"\n{C.CYAN}[PASSO 3] Localizando campo para o código da TV: {codigo_tv} ...{C.RESET}")
        
        preenchido = False

        # Método A: Injeção via DOM (React/Vue/HTML5)
        try:
            js_code = """
            (code) => {
                const inputs = Array.from(document.querySelectorAll("input"));
                // 1. Procura campo único de TV
                for (let inp of inputs) {
                    const ph = (inp.getAttribute('placeholder') || '').toLowerCase();
                    const name = (inp.getAttribute('name') || '').toLowerCase();
                    const id = (inp.id || '').toLowerCase();
                    const max = inp.getAttribute('maxlength');
                    if (max === '6' || ph.includes('ativ') || ph.includes('código') || ph.includes('codigo') || name.includes('code') || id.includes('code')) {
                        inp.focus();
                        inp.value = code;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                // 2. Se houver 6 caixas individuais
                const singleBoxes = inputs.filter(i => i.getAttribute('maxlength') === '1' || i.className.includes('code'));
                if (singleBoxes.length === 6) {
                    for (let i = 0; i < 6; i++) {
                        singleBoxes[i].focus();
                        singleBoxes[i].value = code[i];
                        singleBoxes[i].dispatchEvent(new Event('input', { bubbles: true }));
                        singleBoxes[i].dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    return true;
                }
                return false;
            }
            """
            if page.evaluate(js_code, codigo_tv):
                preenchido = True
                print(f"{C.GREEN}[✓] Código {codigo_tv} inserido com sucesso via DOM!{C.RESET}")
        except Exception as e:
            print(f"[!] Tentativa DOM: {e}")

        # Método B: Se não preencheu via DOM, tenta via Playwright locators
        if not preenchido:
            code_locators = [
                "input[placeholder*='ativação' i]",
                "input[placeholder*='ativacao' i]",
                "input[placeholder*='código' i]",
                "input[placeholder*='codigo' i]",
                "input[maxlength='6']",
                "input[name*='code' i]",
                "input[id*='code' i]",
                "input[type='text']"
            ]
            for sel in code_locators:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        print(f"[*] Campo de código encontrado: {sel}")
                        loc.first.click()
                        loc.first.fill("")
                        loc.first.type(codigo_tv, delay=50)
                        preenchido = True
                        break
                except Exception:
                    pass

        # Método C: Caixas de 1 dígito
        if not preenchido:
            caixas = page.locator("input[maxlength='1']")
            if caixas.count() == 6:
                print("[*] Encontradas 6 caixas individuais para o código.")
                for i in range(6):
                    caixas.nth(i).click()
                    caixas.nth(i).fill(codigo_tv[i])
                    time.sleep(0.05)
                preenchido = True

        if not preenchido:
            print(f"{C.RED}[ERRO] Não foi possível encontrar o campo do código da TV na página.{C.RESET}")
            print(f"URL Atual: {page.url}")
            input(f"\n{C.YELLOW}Verifique o navegador aberto e pressione ENTER para continuar...{C.RESET}")
        else:
            # -------------------------------------------------------------
            # PASSO 4: CLICAR NO BOTÃO DE CONFIRMAR / ATIVAR
            # -------------------------------------------------------------
            print(f"\n{C.CYAN}[PASSO 4] Clicando no botão para Ativar / Conectar TV...{C.RESET}")
            time.sleep(0.5)

            btn_ativar_selectors = [
                "button:has-text('PRONTO')",
                "button:has-text('Pronto')",
                "button:has-text('Ativar')",
                "button:has-text('ATIVAR')",
                "button:has-text('Continuar')",
                "button:has-text('Conectar')",
                "button:has-text('Confirmar')",
                "button[type='submit']"
            ]
            clicou_ativar = False
            for sel in btn_ativar_selectors:
                try:
                    b = page.locator(sel)
                    if b.count() > 0 and b.first.is_visible():
                        print(f"[*] Clicando no botão: {sel}")
                        b.first.click(force=True, timeout=3000)
                        clicou_ativar = True
                        break
                except Exception:
                    pass

            if not clicou_ativar:
                print("[*] Pressionando ENTER para submeter...")
                page.keyboard.press("Enter")

            # -------------------------------------------------------------
            # PASSO 5: VERIFICAR RESULTADO
            # -------------------------------------------------------------
            print(f"\n{C.CYAN}[PASSO 5] Aguardando confirmação da ativação na tela...{C.RESET}")
            time.sleep(3)

            sucesso = False
            mensagem = ""

            for _ in range(15):
                url_final = page.url.lower()
                conteudo = page.content().lower()

                if "exitoso" in url_final or "sucesso" in url_final:
                    sucesso = True
                    mensagem = f"Redirecionado para tela de sucesso ({page.url})"
                    break

                termos_sucesso = [
                    "muito bem", "sua tv foi verificada", "aproveitar o sky",
                    "dispositivo ativado", "vinculado com sucesso", "tela ativada", 
                    "pronto para assistir", "código aceito", "sucesso"
                ]
                for termo in termos_sucesso:
                    if termo in conteudo:
                        sucesso = True
                        mensagem = f"Confirmado na tela: '{termo}'"
                        break
                if sucesso:
                    break

                termos_erro = ["código expirado", "código inválido", "codigo invalido", "limite de telas", "tente novamente"]
                for erro in termos_erro:
                    if erro in conteudo:
                        mensagem = f"Aviso na tela: '{erro}'"
                        break
                if mensagem:
                    break

                time.sleep(1)

            resultado_print = os.path.join(SCREENSHOTS_DIR, f"resultado_{codigo_tv}.png")
            page.screenshot(path=resultado_print)

            tempo_gasto = round(time.time() - inicio, 1)

            print("\n" + "=" * 60)
            if sucesso:
                print(f"{C.GREEN}{C.BOLD}🎉 SUCESSO! SMART TV ATIVADA COM SUCESSO!{C.RESET}")
                print(f"{C.GREEN}Mensagem: {mensagem}{C.RESET}")
            else:
                print(f"{C.YELLOW}{C.BOLD}⚠️ STATUS FINAL DA ATIVAÇÃO:{C.RESET}")
                print(f"Mensagem: {mensagem if mensagem else 'Aguardando confirmação manual na tela'}")
                print(f"URL Final: {page.url}")

            print(f"Tempo total: {tempo_gasto}s")
            print(f"Screenshot salvo em: {resultado_print}")
            print("=" * 60)

        # Captura tokens para diagnóstico e salva para uso via API
        try:
            tokens = page.evaluate("""() => ({
                sessionToken: localStorage.getItem('sessionToken'),
                profileToken: localStorage.getItem('profileToken')
            })""")
            if tokens.get("sessionToken"):
                print(f"\n{C.GREEN}[✓] Token de Sessão JWT capturado com sucesso!{C.RESET}")
                with open(os.path.join(BASE_DIR, "sso_token.txt"), "w", encoding="utf-8") as wf:
                    wf.write(tokens["sessionToken"])
                if tokens.get("profileToken"):
                    with open(os.path.join(BASE_DIR, "profile_token.txt"), "w", encoding="utf-8") as wf:
                        wf.write(tokens["profileToken"])
                print(f"{C.GREEN}[✓] Token atualizado em sso_token.txt para uso imediato em testar_sky_api.py!{C.RESET}")
        except Exception:
            pass

        print(f"\n{C.WHITE}O navegador permanecerá aberto para você conferir a tela.{C.RESET}")
        input(f"{C.CYAN}Pressione [ENTER] no teclado quando desejar fechar o navegador...{C.RESET}")

        browser.close()
        print(f"{C.GREEN}Teste finalizado.{C.RESET}\n")

if __name__ == "__main__":
    try:
        executar_teste()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Teste cancelado pelo usuário.{C.RESET}")
    except Exception as e:
        print(f"\n{C.RED}[ERRO INESPERADO]: {e}{C.RESET}")
        input("\nPressione ENTER para fechar...")
