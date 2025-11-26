import pyautogui
import json
import time
import threading
import os
from datetime import datetime
from pynput import mouse, keyboard
from pynput.keyboard import Key, Controller as KeyboardController
from pathlib import Path

# Configurações de segurança do PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001  # Reduzido para maior velocidade


class TaskRecorder:
    def __init__(self):
        self.recording = False
        self.playing = False
        self.actions = []
        self.record_start_time = None
        self.last_position = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.last_saved_file = None
        try:
            self.keyboard_controller = KeyboardController()
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao inicializar KeyboardController: {e}")
            self.keyboard_controller = None
        
    def start_recording(self):
        """Inicia a gravação das ações"""
        if self.recording:
            print("⚠️ Já está gravando!")
            return
            
        print("🎥 Gravando em 3 segundos...")
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        print("🔴 GRAVANDO! Pressione \\ para parar.")
        
        self.recording = True
        self.actions = []
        self.record_start_time = time.time()
        self.last_position = pyautogui.position()
        
        # Inicia listeners para mouse e teclado
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        
        # Listener para detectar teclas (incluindo parada e gravação)
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        
    def _on_mouse_move(self, x, y):
        """Captura movimento do mouse"""
        if not self.recording:
            return
            
        current_time = time.time() - self.record_start_time
        
        # Só grava se a posição mudou significativamente (reduz ruído e melhora performance)
        if self.last_position:
            dx = abs(x - self.last_position[0])
            dy = abs(y - self.last_position[1])
            # Threshold otimizado: ignora movimentos muito pequenos mas mantém precisão
            # Usa distância euclidiana para melhor detecção
            distance = (dx**2 + dy**2)**0.5
            if distance < 3:  # Ignora movimentos menores que 3 pixels
                return
        
        action = {
            'time': round(current_time, 4),  # Maior precisão no tempo
            'type': 'move',
            'x': int(round(x)),  # Coordenadas inteiras arredondadas para precisão
            'y': int(round(y))
        }
        self.actions.append(action)
        self.last_position = (x, y)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Captura cliques do mouse"""
        if not self.recording:
            return
            
        current_time = time.time() - self.record_start_time
        
        if pressed:  # Só grava quando pressiona, não quando solta
            action = {
                'time': round(current_time, 4),  # Maior precisão no tempo
                'type': 'click',
                'x': int(x),  # Coordenadas inteiras para precisão
                'y': int(y),
                'button': str(button).split('.')[-1]  # 'left', 'right', 'middle'
            }
            self.actions.append(action)
            print(f"   📍 Clique {button} em ({x}, {y})")
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Captura scroll do mouse"""
        if not self.recording:
            return
            
        current_time = time.time() - self.record_start_time
        
        action = {
            'time': round(current_time, 4),  # Maior precisão no tempo
            'type': 'scroll',
            'x': int(x),  # Coordenadas inteiras para precisão
            'y': int(y),
            'dx': dx,
            'dy': dy
        }
        self.actions.append(action)
        print(f"   📜 Scroll em ({x}, {y})")
    
    def _key_to_string(self, key):
        """Converte uma tecla do pynput para string legível"""
        try:
            # Teclas especiais do pynput
            if isinstance(key, Key):
                return key.name
            # Caracteres normais
            elif hasattr(key, 'char') and key.char:
                return key.char
            # Fallback
            else:
                key_str = str(key)
                # Remove prefixos comuns
                if 'KeyCode' in key_str:
                    if hasattr(key, 'char') and key.char:
                        return key.char
                    elif hasattr(key, 'vk'):
                        # Tenta converter código virtual para caractere
                        return chr(key.vk) if 32 <= key.vk <= 126 else f"vk_{key.vk}"
                return key_str
        except Exception as e:
            return str(key)
    
    def _on_key_press(self, key):
        """Captura teclas pressionadas durante a gravação"""
        if not self.recording:
            return
        
        # Verifica se é a tecla de parar gravação
        if is_key_pressed(key, '\\'):
            self.stop_recording()
            return
        
        # Ignora teclas de controle do próprio sistema
        if is_key_pressed(key, ';') or is_key_pressed(key, '/'):
            return
        
        current_time = time.time() - self.record_start_time
        
        # Converte a tecla para string legível
        key_str = self._key_to_string(key)
        is_special = isinstance(key, Key) or not (hasattr(key, 'char') and key.char)
        
        action = {
            'time': round(current_time, 4),  # Maior precisão no tempo
            'type': 'key_press',
            'key': key_str,
            'is_special': is_special,
            'key_obj': str(key)  # Para debug
        }
        self.actions.append(action)
        print(f"   ⌨️ Tecla pressionada: {key_str}")
    
    def _on_key_release(self, key):
        """Captura teclas soltas durante a gravação (opcional, para maior precisão)"""
        if not self.recording:
            return
        
        # Ignora teclas de controle
        if is_key_pressed(key, '\\') or is_key_pressed(key, ';') or is_key_pressed(key, '/'):
            return
        
        # Não grava key_release para simplificar (key_press já faz press+release)
        # Mas pode ser útil para combinações de teclas no futuro
        pass
    
    def stop_recording(self):
        """Para a gravação"""
        if not self.recording:
            return
            
        self.recording = False
        
        # Para os listeners
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        print("⏹️ Gravação parada.")
        print(f"📊 Total de ações gravadas: {len(self.actions)}")
        self.save_recording()
    
    def _get_recordings_dir(self):
        """Obtém o diretório de gravações, criando se necessário"""
        # Tenta criar no diretório do script primeiro
        script_dir = Path(__file__).parent.absolute()
        recordings_dir = script_dir / "recordings"
        
        try:
            recordings_dir.mkdir(exist_ok=True)
            return recordings_dir
        except (PermissionError, OSError):
            # Se falhar, tenta no diretório do usuário
            try:
                user_dir = Path.home() / "PyAutoGUI_recordings"
                user_dir.mkdir(exist_ok=True)
                return user_dir
            except (PermissionError, OSError):
                # Último recurso: diretório atual
                try:
                    current_dir = Path.cwd() / "recordings"
                    current_dir.mkdir(exist_ok=True)
                    return current_dir
                except (PermissionError, OSError) as e:
                    print(f"❌ Erro ao criar diretório de gravações: {e}")
                    # Retorna None e salva no diretório atual
                    return Path.cwd()
    
    def save_recording(self):
        """Salva as ações em arquivo JSON"""
        if not self.actions:
            print("⚠️ Nenhuma ação para salvar!")
            return
            
        filename = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Obtém ou cria diretório de gravações
        recordings_dir = self._get_recordings_dir()
        
        filepath = recordings_dir / filename
        
        recording_data = {
            'created_at': datetime.now().isoformat(),
            'total_actions': len(self.actions),
            'duration': self.actions[-1]['time'] if self.actions else 0,
            'actions': self.actions
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(recording_data, f, indent=2, ensure_ascii=False)
            
            self.last_saved_file = str(filepath)
            print(f"💾 Ações salvas em {filepath}")
            return str(filepath)
        except (PermissionError, OSError) as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            print(f"   Tentando salvar no diretório atual...")
            # Tenta salvar no diretório atual como último recurso
            try:
                filepath = Path.cwd() / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(recording_data, f, indent=2, ensure_ascii=False)
                self.last_saved_file = str(filepath)
                print(f"💾 Ações salvas em {filepath}")
                return str(filepath)
            except Exception as e2:
                print(f"❌ Erro crítico ao salvar: {e2}")
                return None
    
    def _find_recordings_dir(self):
        """Encontra o diretório de gravações em locais possíveis"""
        # Lista de locais possíveis
        possible_dirs = [
            Path(__file__).parent.absolute() / "recordings",
            Path.home() / "PyAutoGUI_recordings",
            Path.cwd() / "recordings",
            Path.cwd()  # Diretório atual como último recurso
        ]
        
        for dir_path in possible_dirs:
            if dir_path.exists() and dir_path.is_dir():
                json_files = list(dir_path.glob("task_*.json"))
                if json_files:
                    return dir_path
        
        # Se não encontrou nenhum, retorna o primeiro que pode ser criado
        return possible_dirs[0]
    
    def load_recording(self, filename=None):
        """Carrega gravação do arquivo"""
        if filename is None:
            filename = self.last_saved_file
            
        if filename is None:
            # Tenta carregar o arquivo mais recente
            recordings_dir = self._find_recordings_dir()
            
            if recordings_dir.exists():
                json_files = list(recordings_dir.glob("task_*.json"))
                if json_files:
                    filename = str(max(json_files, key=lambda p: p.stat().st_mtime))
                    print(f"📂 Carregando arquivo mais recente: {filename}")
                else:
                    print("❌ Nenhum arquivo de gravação encontrado!")
                    return False
            else:
                print("❌ Diretório de gravações não existe!")
                return False
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.actions = data.get('actions', data)  # Compatibilidade com formato antigo
                self.last_saved_file = filename
                print(f"✅ Gravação carregada: {len(self.actions)} ações")
                return True
        except FileNotFoundError:
            print(f"❌ Arquivo não encontrado: {filename}")
            return False
        except json.JSONDecodeError:
            print(f"❌ Erro ao ler arquivo JSON: {filename}")
            return False
    
    def play_recording(self, loops=1, delay=1, speed=1.0):
        """Reproduz a gravação"""
        if not self.actions:
            print("❌ Nenhuma gravação carregada!")
            return
        
        if self.playing:
            print("⚠️ Já está reproduzindo!")
            return
        
        print(f"🎬 Reproduzindo {loops} vez(es) (velocidade: {speed}x)...")
        print("   Pressione \\ para parar a reprodução")
        
        # Listener para parar reprodução
        stop_listener = keyboard.Listener(on_press=self._on_key_press_stop)
        stop_listener.start()
        
        try:
            for loop in range(loops):
                if not self.playing and loop > 0:
                    break
                    
                print(f"\n🔁 Loop {loop + 1}/{loops}")
                self.playing = True
                
                start_time = time.time()
                previous_action_time = 0
                
                for i, action in enumerate(self.actions):
                    if not self.playing:
                        print("⏹️ Reprodução interrompida pelo usuário")
                        break
                    
                    # Calcula tempo preciso para a ação
                    elapsed_time = time.time() - start_time
                    action_time = action['time'] / speed  # Aplica velocidade
                    
                    # Espera o momento certo (com tolerância mínima para evitar delays desnecessários)
                    wait_time = action_time - elapsed_time
                    if wait_time > 0.005:  # Só espera se for mais que 5ms (otimizado)
                        time.sleep(wait_time)
                    elif wait_time < 0:
                        # Se estiver atrasado, continua sem esperar (não acumula atraso)
                        pass
                    
                    # Executa ação
                    try:
                        if action['type'] == 'move':
                            # Movimento instantâneo (duration=0) para maior velocidade
                            pyautogui.moveTo(action['x'], action['y'], duration=0)
                            
                        elif action['type'] == 'click':
                            button = action.get('button', 'left')
                            # Move e clica rapidamente (moveTo já posiciona, então clica direto)
                            pyautogui.moveTo(action['x'], action['y'], duration=0)
                            pyautogui.mouseDown(button=button)
                            pyautogui.mouseUp(button=button)
                            
                        elif action['type'] == 'scroll':
                            pyautogui.scroll(int(action['dy'] * 3), x=action['x'], y=action['y'])
                            
                        elif action['type'] == 'key_press':
                            self._reproduce_key(action)
                            
                    except Exception as e:
                        print(f"⚠️ Erro ao executar ação {i}: {e}")
                        continue
                
                # Delay entre loops
                if loop < loops - 1 and self.playing:
                    print(f"⏳ Aguardando {delay} segundos antes do próximo loop...")
                    for _ in range(delay):
                        if not self.playing:
                            break
                        time.sleep(1)
        
        finally:
            stop_listener.stop()
            self.playing = False
        
        print("\n✅ Execução concluída!")
    
    def _on_key_press_stop(self, key):
        """Detecta tecla \ para parar reprodução"""
        if is_key_pressed(key, '\\') and self.playing:
            self.stop_playing()
    
    def _reproduce_key(self, action):
        """Reproduz uma tecla pressionada"""
        key_str = action['key']
        is_special = action.get('is_special', False)
        
        try:
            if is_special:
                # Mapeia teclas especiais para objetos Key do pynput
                key_map = {
                    'ctrl_l': Key.ctrl_l,
                    'ctrl_r': Key.ctrl_r,
                    'ctrl': Key.ctrl,
                    'alt_l': Key.alt_l,
                    'alt_r': Key.alt_r,
                    'alt': Key.alt,
                    'shift': Key.shift,
                    'shift_l': Key.shift_l,
                    'shift_r': Key.shift_r,
                    'tab': Key.tab,
                    'enter': Key.enter,
                    'space': Key.space,
                    'backspace': Key.backspace,
                    'delete': Key.delete,
                    'esc': Key.esc,
                    'escape': Key.esc,
                    'up': Key.up,
                    'down': Key.down,
                    'left': Key.left,
                    'right': Key.right,
                    'home': Key.home,
                    'end': Key.end,
                    'page_up': Key.page_up,
                    'page_down': Key.page_down,
                    'f1': Key.f1,
                    'f2': Key.f2,
                    'f3': Key.f3,
                    'f4': Key.f4,
                    'f5': Key.f5,
                    'f6': Key.f6,
                    'f7': Key.f7,
                    'f8': Key.f8,
                    'f9': Key.f9,
                    'f10': Key.f10,
                    'f11': Key.f11,
                    'f12': Key.f12,
                }
                
                key_lower = key_str.lower()
                if key_lower in key_map:
                    # Usa KeyboardController do pynput para teclas especiais
                    if self.keyboard_controller:
                        self.keyboard_controller.press(key_map[key_lower])
                        time.sleep(0.001)  # Reduzido para maior velocidade
                        self.keyboard_controller.release(key_map[key_lower])
                    else:
                        # Fallback se keyboard_controller não estiver disponível
                        pyautogui.press(key_lower)
                else:
                    # Tenta usar pyautogui como fallback
                    try:
                        pyautogui.press(key_lower)
                    except:
                        print(f"   ⚠️ Tecla especial não mapeada: {key_str}")
            else:
                # Para teclas normais (caracteres)
                if len(key_str) == 1:
                    # Usa KeyboardController para maior confiabilidade
                    if self.keyboard_controller:
                        self.keyboard_controller.type(key_str)
                    else:
                        # Fallback se keyboard_controller não estiver disponível
                        pyautogui.write(key_str)
                else:
                    # Tenta usar pyautogui
                    try:
                        pyautogui.press(key_str.lower())
                    except:
                        print(f"   ⚠️ Erro ao pressionar tecla: {key_str}")
        except Exception as e:
            print(f"   ⚠️ Erro ao reproduzir tecla {key_str}: {e}")
    
    def stop_playing(self):
        """Para a reprodução"""
        if self.playing:
            self.playing = False
            print("⏹️ Parando reprodução...")


def is_key_pressed(key, target_char):
    """Verifica se a tecla pressionada corresponde ao caractere alvo"""
    try:
        if hasattr(key, 'char') and key.char:
            return key.char == target_char
        # Fallback para códigos virtuais (Windows)
        if hasattr(key, 'vk'):
            char_map = {
                ';': [186, 59],   # Ponto e vírgula
                '\\': [92, 220],  # Barra invertida
                '/': [191, 111]   # Barra
            }
            if target_char in char_map:
                return key.vk in char_map[target_char]
    except (AttributeError, TypeError):
        pass
    return False


def show_status(recorder):
    """Mostra status atual do gravador"""
    status = []
    if recorder.recording:
        status.append("🔴 GRAVANDO")
    if recorder.playing:
        status.append("▶️ REPRODUZINDO")
    if not recorder.recording and not recorder.playing:
        status.append("⚪ OCIOSO")
    
    return " | ".join(status) if status else "⚪ OCIOSO"


def main():
    try:
        recorder = TaskRecorder()
    except Exception as e:
        print(f"❌ Erro ao inicializar TaskRecorder: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️ Pressione Enter para fechar...")
        input()
        return
    
    print("=" * 60)
    print("🤖 GRAVADOR DE TAREFAS AUTOMATIZADO")
    print("=" * 60)
    print("\n📋 Controles:")
    print("   ; (ponto e vírgula) - Gravar nova tarefa")
    print("   \\ (barra invertida) - Parar gravação/reprodução")
    print("   / (barra) - Reproduzir última gravação (1 vez)")
    print("   F4 - Reproduzir última gravação (3 vezes)")
    print("   F5 - Carregar gravação do arquivo")
    print("   ESC - Sair")
    print("\n" + "=" * 60)
    
    # Listener global para hotkeys
    def on_key_press(key):
        try:
            # Detecta ponto e vírgula (;) para gravar
            if is_key_pressed(key, ';'):
                if not recorder.recording and not recorder.playing:
                    recorder.start_recording()
                else:
                    print("⚠️ Pare a gravação/reprodução atual primeiro!")
                    
            # Detecta barra invertida (\) para parar
            elif is_key_pressed(key, '\\'):
                if recorder.recording:
                    recorder.stop_recording()
                elif recorder.playing:
                    recorder.stop_playing()
                else:
                    print("ℹ️ Nenhuma operação ativa para parar")
                    
            # Detecta barra (/) para reproduzir
            elif is_key_pressed(key, '/'):
                if not recorder.recording and not recorder.playing:
                    if recorder.actions or recorder.load_recording():
                        recorder.play_recording(loops=1, delay=0, speed=1.0)
                    else:
                        print("❌ Nenhuma gravação disponível!")
                else:
                    print("⚠️ Pare a operação atual primeiro!")
                    
            elif key == keyboard.Key.f4:
                if not recorder.recording and not recorder.playing:
                    if recorder.actions or recorder.load_recording():
                        recorder.play_recording(loops=3, delay=2, speed=1.0)
                    else:
                        print("❌ Nenhuma gravação disponível!")
                else:
                    print("⚠️ Pare a operação atual primeiro!")
                    
            elif key == keyboard.Key.f5:
                if not recorder.recording and not recorder.playing:
                    filename = input("\n📂 Digite o nome do arquivo (ou Enter para o mais recente): ").strip()
                    if filename:
                        recorder.load_recording(filename)
                    else:
                        recorder.load_recording()
                else:
                    print("⚠️ Pare a operação atual primeiro!")
                    
            elif key == keyboard.Key.esc:
                if recorder.recording:
                    recorder.stop_recording()
                if recorder.playing:
                    recorder.stop_playing()
                print("\n👋 Saindo...")
                return False
                
        except AttributeError:
            pass
        
        return True
    
    # Inicia listener de teclado
    listener = None
    try:
        listener = keyboard.Listener(on_press=on_key_press)
        listener.start()
        print("✅ Listener de teclado iniciado com sucesso!")
        print("⏳ Aguardando comandos...\n")
    except Exception as e:
        print(f"❌ Erro ao iniciar listener de teclado: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️ Pressione Enter para fechar...")
        input()
        return
    
    try:
        # Loop principal com status
        last_status = ""
        while listener.running:
            try:
                current_status = show_status(recorder)
                if current_status != last_status:
                    print(f"\n📊 Status: {current_status}")
                    last_status = current_status
                time.sleep(0.5)
            except Exception as e:
                print(f"\n⚠️ Erro no loop principal: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Saindo...")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if recorder.recording:
                recorder.stop_recording()
            if recorder.playing:
                recorder.stop_playing()
            if listener:
                listener.stop()
        except:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        import traceback
        print("\n📋 Detalhes do erro:")
        traceback.print_exc()
        print("\n⚠️ Pressione Enter para fechar...")
        input()
    else:
        # Se sair normalmente, também pausa para ver mensagens
        print("\n⚠️ Pressione Enter para fechar...")
        input()

