# 🛠️ Como Configurar seu Github para que a IA funcione

Antes que a magia dos "Botões da seção Actions" possa funcionar e fazer buscas automáticas para você no Youtube através do **Gemini IA**, o GitHub precisa de algumas permissões extras.

Pense assim: O Google distribui as "chaves de acesso" para a Inteligência Artificial dele (API Keys). E o seu GitHub (a plataforma que hospedará os robôs) precisa *ter* uma chave para saber que é a "*Sua Conta*" que está pagando ou usando os créditos grátis do Gemini.

Siga exatamente os passos abaixo e tudo estará rodando em menos de 5 minutos:

---

### Passo 1: Habilitar o uso da funcionalidade "Actions" (Os Robôs Cloud)

Por razões de segurança, contas novas às vezes possuem o sistema de automação desativado. Vamos garantir que eles possam rodar seus relatórios.

1. Abra a página principal deste repositório no seu GitHub.
2. Na barra superior horizontal clica na aba de **"Settings"** (o ícone de engrenagem transparente).
3. Na barra lateral esquerda (do menu grande cheio de opções), clique em **"Actions"** e logo abaixo em **"General"**.
4. Procure a opção "Actions permissions" no topo e marque a bolinha em **"Allow all actions and reusable workflows"**.
5. Salve a tela. (Se já estiver habilitado, você não precisa se preocupar).

---

### Passo 2: Pegar sua Chave ("API Key") do Gemini no Google

A inteligência utilizada é o **Google Gemini 2.5 Flash**, que possui um excelente pacote generoso gratuito por mês e faz análise de vídeos longos rapidamente!

1. Acesse o estúdio oficial do Google focado em IA: (você precisará ter ou estar logado em uma conta `@gmail.com` sua): 
   [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Concorde com os termos se for o primeiro acesso.
3. Clique grandão no botão **"Get API key"** ou **"Create API Key"** na parte superior esquerda.
4. Escolha **"Create API key in new project"** se não tiver criado nenhum.
5. Copie a sequência absurdamente grande de letras, números e traços que ele te der. (Exemplo: `AIzaSyC2V...P_3b-E`).
6. **Não perca este código, não mostre a ninguém e segure ele no seu "Ctrl + C" do computador!**

---

### Passo 3: Colocar a Chave de forma Segura no "Cofre" do Github

Nós não queremos nunca colar esse código visível para todo o público, por isso vamos escondê-lo no "Cofre Secreto" (*Secrets*) do seu projeto. O seu robô saberá ler de lá automaticamente.

1. Volte ao seu repositório oficial aqui no GitHub e retorne para a aba mestra **"Settings"** (A engrenagem).
2. Na aba de menu lateral à esquerda, role para baixo até ver: **"Secrets and variables"**. E então clique na opção **"Actions"**.
3. Nesta nova tela, no centro aparecerá a parte "Repository secrets". 
4. Clique no botão verdinho à direita escrito: **"New repository secret"**.
5. Haverá duas caixas. Você preencherá elas exatamente com essas duas formas:
   * Em **Name:** Digite tudo maiúsculo e perfeitamente assim (sem espaços):
     `GEMINI_API_KEY`
   * Em **Secret:** Dê o Ctrl+V para "colar" aquela grandessíssima chave estranha que o Google te deu no *Passo 2*.
6. Clique no grande botão verde de **Add secret**.

**Pronto! A integração e a magia estão finalizadas.**
O robô agora estará oficialmente conectado aos seus créditos gratuitos da Google, liberando você para extrair, analisar e caçar cenas no YouTube. Já pode seguir as instruções que te ensinei lá no `README.md` principal em como caçar e baixar suas cenas.
