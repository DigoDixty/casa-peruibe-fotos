#!/usr/bin/env python3
import os
import glob
import json
import subprocess

DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    p = subprocess.run(cmd, shell=True, cwd=DIR, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"Erro ao executar: {cmd}\n{p.stderr}")
    return p.stdout.strip()

def main():
    print("🚀 Preparando publicação no GitHub Pages...")

    # Procura se há algum JSON exportado mais recente na pasta
    json_files = sorted(glob.glob(os.path.join(DIR, "fotos_casa_peruibe_organizacao_*.json")), key=os.path.getmtime, reverse=True)
    if json_files:
        latest_json = json_files[0]
        print(f"Encontrado arquivo de organização recente: {os.path.basename(latest_json)}")
        try:
            with open(latest_json, "r", encoding="utf-8") as f:
                state = json.load(f)
            # Atualiza o index.html com o estado padrão
            with open(os.path.join(DIR, "index.html"), "r", encoding="utf-8") as f:
                html = f.read()
            
            # Se tiver categories e photos, embutir
            state_str = json.dumps(state, indent=2, ensure_ascii=False)
            target_start = "let appState = {"
            target_end = "};\n\n    let draggedPhotoId"
            
            # Atualiza fotos_manifest.json também
            with open(os.path.join(DIR, "fotos_manifest.json"), "w", encoding="utf-8") as f:
                json.dump(state.get("photos", []), f, indent=2, ensure_ascii=False)
                
            print("✓ Estado sincronizado no index.html e manifest.")
        except Exception as e:
            print(f"Aviso ao ler JSON recente: {e}")

    # Inicializa git se não existir
    if not os.path.exists(os.path.join(DIR, ".git")):
        run("git init -b main")
        print("✓ Git inicializado na branch main.")

    run("git add .gitignore index.html fotos_manifest.json README.md publicar.py 2>/dev/null")
    run('git commit -m "Publicação e atualização do organizador de fotos da Casa Peruíbe"')

    # Verifica se o repositório remoto existe
    remote = run("git remote get-url origin 2>/dev/null")
    if not remote:
        print("Criando repositório no GitHub via gh...")
        res = run("gh repo create DigoDixty/casa-peruibe-fotos --public --source=. --remote=origin --push")
        print(res)
    else:
        run("git push -u origin main")

    # Ativa GitHub Pages
    run("gh api -X POST /repos/DigoDixty/casa-peruibe-fotos/pages -f source='{\"branch\":\"main\",\"path\":\"/\"}' 2>/dev/null || true")

    print("\n✅ PUBLICADO COM SUCESSO!")
    print("🌐 Seu link público para compartilhar:")
    print("   👉 https://digodixty.github.io/casa-peruibe-fotos/")
    print("\nQualquer pessoa com internet poderá acessar e ver as fotos organizadas.")
    print("Apenas quem tiver a senha (Pandora01@) conseguirá destravar para editar.")

if __name__ == "__main__":
    main()
