# 🎬 Sucram Finder
<img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/d1ca30a5-f3c0-4358-834c-b1a4a82682d6" />

Este projeto é uma ferramenta de IA projetada para ajudar editores de vídeo a encontrarem cenas específicas no YouTube de forma automática, utilizando o poder da inteligência artificial (Google Gemini).

Todo o esforço de download pesado e processamento de IA roda **diretamente na nuvem do GitHub**, não ocupando o hardware do seu computador durante a busca.

---

## 🚀 Como Usar a Ferramenta na Nuvem

Todo o uso da ferramenta pode ser feito através do próprio site do **GitHub**, sem precisar instalar programas suspeitos ou pesados no seu computador. O uso é dividido em **Duas Fases independentes**, disponíveis na aba **"Actions"** no topo da tela.

### Fase 1: Encontrar as Cenas (O Robô Explorador)
Nesta fase, a Inteligência Artificial fará o trabalho sujo de varrer o YouTube para você, encontrar vídeos que contenham seu tema e mapear exatamente em quais *minutos e segundos* a cena aparece, gerando um relatório em `.txt` e *Alguns Prints ("fotografias")* dos vídeos.

1. Clique na aba **"Actions"** na barra superior do seu repositório.
2. No menu à esquerda, clique na automação chamada **"Fase 1: Buscar Cenas (Gemini)"**.
3. Na direita, você verá um botão azul chamado **"Run workflow"**, clique nele.
4. Preencha as informações que ele vai te pedir:
   * **theme:** Qual a sua cena alvo? (Ex: *Cachorro brincando na areia* | *Casas em marrocos*). Seja específico!
   * **limit:** Quantos vídeos no máximo a IA deve testar e varrer? (Ex: `30` ou `50`).
5. Clique em **"Run workflow"** (Botão verde).
6. Aguarde alguns minutos enquanto o robô trabalha! 
7. Quando tudo ficar com uma "marquinha verde de concluído", abra a tarefa recém-terminada e desça até a seção **"Artifacts"**.
8. Baixe o arquivo zip de resultados! Lá dentro estará o seu relatório de cenas `relatorio_cenas.txt` com todas as minutagens exatas e os prints em `.jpg`.

---

### Fase 2: Baixar seu Vídeo Favorito em Alta Qualidade (HD/4K)
Ao ler o relatório no Passo 1, você reparou que a cena que você quer baixar pertence ao **Vídeo 1**, **Vídeo 4** e **Vídeo 7**. Agora, precisamos desses vídeos na melhor qualidade possível.

1. Clique na aba **"Actions"** novamente.
2. No menu à esquerda, selecione **"Fase 2: Download HD -> GitHub Artifacts"**.
3. Clique em **Run workflow**.
4. **video_indices**: Digite os números dos vídeos que você quer baixar, separados por vírgula. Exemplo: `1, 4, 7` ou apenas `5`
5. Clique em **"Run workflow"**.
6. A nuvem do GitHub agora baixará silenciosamente apenas os vídeos escolhidos, juntando a melhor qualidade de Áudio e Vídeo disponíveis originais.
7. Aguarde a automação concluir (marquinha verde). 
8. Role até a parte inferior, na seção **"Artifacts"** e baixe o seu arquivo com os `.mp4` impecáveis para colocar direto no seu Premiere ou CapCut.
