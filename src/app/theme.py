"""Identidade visual do Porto Alfa — "ponte de comando".

Paleta náutica noturna:
  * azul-oceano profundo para o fundo,
  * ciano de instrumento (radar/sonar) para interação e dados,
  * âmbar de farol como acento de marca, usado com parcimônia.
"""

from __future__ import annotations

from html import escape

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700&display=swap');

:root{
  --pa-fundo:#060F1A;
  --pa-superficie:#0C1D2E;
  --pa-elevado:#12293F;
  --pa-linha:rgba(148,197,230,.16);
  --pa-ciano:#38BDF8;
  --pa-ciano-esc:#0EA5E9;
  --pa-ambar:#F6A83C;
  --pa-texto:#E8F1F8;
  --pa-suave:#8FA9C0;
  --pa-suave-2:#6E88A3;
  --pa-ok:#34D399;
  --pa-fonte:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
  --pa-display:'Sora','Inter',system-ui,sans-serif;
  --pa-mono:ui-monospace,'Cascadia Mono','JetBrains Mono',Consolas,monospace;
}

/* ===================== BASE ===================== */
html, body{ background:#060F1A !important; }

[data-testid="stAppViewContainer"], .stApp{
  font-family:var(--pa-fonte);
  color:var(--pa-texto);
  background:
    radial-gradient(1100px 560px at 92% -12%, rgba(56,189,248,.20), transparent 62%),
    radial-gradient(760px 440px at -6% 4%, rgba(246,168,60,.09), transparent 60%),
    linear-gradient(180deg,#071320 0%, #060F1A 52%, #050C15 100%) !important;
}

[data-testid="stHeader"], [data-testid="stToolbar"]{
  background:transparent !important;
  box-shadow:none !important;
}

[data-testid="stMainBlockContainer"]{
  max-width:1000px !important;
  padding-top:1.1rem !important;
  padding-bottom:4.5rem !important;
}

/* ===================== LATERAL ===================== */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#081726 0%, #060F1A 100%) !important;
  border-right:1px solid var(--pa-linha) !important;
}
[data-testid="stSidebarHeader"]{ background:transparent !important; }
[data-testid="stSidebarContent"]{ padding-top:1.4rem !important; }

.pa-marca{ display:flex; align-items:center; gap:.85rem; margin-bottom:1.15rem; }
.pa-logo{
  width:52px; height:52px; border-radius:17px;
  display:flex; align-items:center; justify-content:center;
  background:linear-gradient(150deg, rgba(56,189,248,.24), rgba(14,165,233,.08));
  border:1px solid rgba(56,189,248,.36);
  box-shadow:0 16px 32px -20px rgba(56,189,248,.95);
}
.pa-nome{
  font-family:var(--pa-display); font-size:1.2rem; font-weight:700;
  letter-spacing:-.015em; color:#F2F8FD; line-height:1.1;
}
.pa-sub{
  font-size:.68rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--pa-suave-2); margin-top:.34rem; font-weight:600;
}
.pa-regua{
  height:1px; margin:1.15rem 0;
  background:linear-gradient(90deg, rgba(56,189,248,.55), rgba(56,189,248,0));
}
.pa-info{ display:flex; flex-direction:column; gap:.5rem; margin-bottom:1rem; }
.pa-campo{
  background:rgba(12,29,46,.62); border:1px solid var(--pa-linha);
  border-radius:13px; padding:.6rem .8rem;
}
.pa-campo b{
  display:block; font-size:.58rem; letter-spacing:.17em; text-transform:uppercase;
  color:var(--pa-suave-2); font-weight:700; margin-bottom:.28rem;
}
.pa-campo span{
  font-size:.82rem; color:#CFE3F2; font-family:var(--pa-mono); word-break:break-all;
}
.pa-rodape{
  font-size:.7rem; color:var(--pa-suave-2); line-height:1.55; margin-top:1.1rem;
}

/* ===================== CABEÇALHO ===================== */
.pa-hero{
  position:relative; overflow:hidden;
  background:linear-gradient(160deg, rgba(18,41,63,.92), rgba(9,22,36,.92));
  border:1px solid var(--pa-linha);
  border-radius:26px;
  padding:2.1rem 2.4rem 2.5rem;
  margin:.2rem 0 2.1rem;
  box-shadow:0 46px 90px -56px rgba(0,0,0,1);
}
.pa-hero::before{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(620px 220px at 86% -34%, rgba(56,189,248,.30), transparent 70%);
}
.pa-eyebrow{
  position:relative; display:inline-flex; align-items:center; gap:.5rem;
  font-size:.64rem; letter-spacing:.19em; font-weight:700; text-transform:uppercase;
  color:#9BE1FF; background:rgba(56,189,248,.10);
  border:1px solid rgba(56,189,248,.32);
  padding:.38rem .82rem; border-radius:999px; margin-bottom:1.15rem;
}
.pa-ponto{
  width:7px; height:7px; border-radius:50%; background:var(--pa-ok);
  animation:paPulso 2.2s infinite;
}
@keyframes paPulso{
  0%{ box-shadow:0 0 0 0 rgba(52,211,153,.6) }
  70%{ box-shadow:0 0 0 8px rgba(52,211,153,0) }
  100%{ box-shadow:0 0 0 0 rgba(52,211,153,0) }
}
.pa-hero h1{
  position:relative; font-family:var(--pa-display);
  font-size:clamp(1.7rem, 3.3vw, 2.45rem);
  line-height:1.14; letter-spacing:-.028em; font-weight:700;
  color:#F2F8FD; margin:0 0 .7rem; max-width:20ch;
}
.pa-hero h1 em{
  font-style:normal;
  background:linear-gradient(100deg,#FBBF24,#F6A83C);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.pa-hero p{
  position:relative; color:var(--pa-suave);
  font-size:1.02rem; line-height:1.62; margin:0; max-width:60ch;
}
.pa-onda{
  position:absolute; right:0; bottom:0; width:58%; height:135px;
  opacity:.6; pointer-events:none;
}

/* ===================== CONVERSA ===================== */
[data-testid="stChatMessage"]{
  background:transparent !important; border:none !important; padding:0 !important;
  gap:.75rem; align-items:flex-start; margin:0 0 1.5rem !important;
}
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"]{
  width:40px; height:40px; min-width:40px; border-radius:14px !important;
  display:flex; align-items:center; justify-content:center;
  border:1px solid rgba(255,255,255,.12) !important;
  box-shadow:0 12px 24px -16px rgba(0,0,0,.95) !important;
  margin-top:.15rem;
}
[data-testid="stChatMessageAvatarAssistant"]{
  background:linear-gradient(135deg,#38BDF8,#0EA5E9) !important;
  color:#04121F !important;
}
[data-testid="stChatMessageAvatarUser"]{
  background:linear-gradient(135deg,#FBBF24,#F6A83C) !important;
  color:#2B1A04 !important;
}
[data-testid="stChatMessageAvatarUser"] [data-testid="stIconMaterial"],
[data-testid="stChatMessageAvatarAssistant"] [data-testid="stIconMaterial"]{ color:inherit !important; }

/* --- bolha do usuário --- */
[data-testid="stChatMessageAvatarUser"] ~ [data-testid="stChatMessageContent"]{
  background:linear-gradient(135deg, rgba(14,165,233,.96), rgba(56,189,248,.92)) !important;
  border:none !important;
  border-radius:20px 20px 6px 20px !important;
  padding:.9rem 1.2rem !important;
  max-width:78%;
  box-shadow:0 24px 46px -30px rgba(14,165,233,.95) !important;
}
[data-testid="stChatMessageAvatarUser"] ~ [data-testid="stChatMessageContent"] p{ color:#03121F !important; }
[data-testid="stChatMessageAvatarUser"] ~ [data-testid="stChatMessageContent"] strong{ color:#02101A !important; }

/* --- bolha do assistente --- */
[data-testid="stChatMessageAvatarAssistant"] ~ [data-testid="stChatMessageContent"]{
  background:linear-gradient(180deg, rgba(18,41,63,.94), rgba(11,26,42,.94)) !important;
  border:1px solid var(--pa-linha) !important;
  border-radius:6px 22px 22px 22px !important;
  padding:1.15rem 1.35rem 1.25rem !important;
  max-width:90%;
  box-shadow:0 34px 64px -44px rgba(0,0,0,1) !important;
}

/* --- tipografia dentro das mensagens --- */
[data-testid="stChatMessageContent"]{ line-height:1.62; }
[data-testid="stChatMessageContent"] p{ margin:.4rem 0; font-size:1rem; }
[data-testid="stChatMessageContent"] p:first-child{ margin-top:0; }
[data-testid="stChatMessageContent"] p:last-child{ margin-bottom:0; }
[data-testid="stChatMessageContent"] strong{ color:#FFFFFF !important; font-weight:650; }
[data-testid="stChatMessageContent"] h1,
[data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3{
  font-family:var(--pa-display); color:#F2F8FD;
  letter-spacing:-.015em; margin:1rem 0 .5rem; line-height:1.25;
}
[data-testid="stChatMessageContent"] ul,
[data-testid="stChatMessageContent"] ol{ margin:.5rem 0; padding-left:1.25rem; }
[data-testid="stChatMessageContent"] li{ margin:.3rem 0; }
[data-testid="stChatMessageContent"] code{
  font-family:var(--pa-mono);
  background:rgba(56,189,248,.13); color:#A8E4FF;
  border:1px solid rgba(56,189,248,.22);
  padding:.12rem .44rem; border-radius:7px; font-size:.87em;
}
[data-testid="stChatMessageContent"] pre{
  background:#08182A !important; border:1px solid var(--pa-linha);
  border-radius:13px; padding:.95rem 1.05rem;
}
[data-testid="stChatMessageContent"] hr{
  border:none; border-top:1px solid var(--pa-linha);
  margin:1.05rem 0 .95rem;
}

/* --- rodapé da resposta: instrumentos + fontes --- */
.pa-rodape-resp{ margin-top:1.05rem; }
.pa-fontes{ display:flex; flex-wrap:wrap; align-items:center; gap:.42rem; margin-top:.9rem; }
.pa-rot{
  font-size:.6rem; letter-spacing:.17em; font-weight:700; text-transform:uppercase;
  color:var(--pa-suave-2); margin-right:.15rem;
}
.pa-chip{
  display:inline-flex; align-items:center; gap:.4rem;
  font-size:.74rem; font-family:var(--pa-fonte); color:#9BE1FF;
  background:rgba(56,189,248,.10); border:1px solid rgba(56,189,248,.30);
  padding:.24rem .64rem; border-radius:999px;
  max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.pa-chip::before{
  content:""; width:5px; height:5px; border-radius:50%;
  background:var(--pa-ciano); flex:none; opacity:.9;
}

[data-testid="stMetric"]{
  background:linear-gradient(180deg, rgba(56,189,248,.09), rgba(56,189,248,.03));
  border:1px solid rgba(56,189,248,.22);
  border-radius:14px; padding:.6rem .85rem .68rem;
}
[data-testid="stMetricLabel"] p{
  font-size:.6rem !important; letter-spacing:.15em; text-transform:uppercase;
  font-weight:700; color:var(--pa-suave-2) !important; margin:0;
}
[data-testid="stMetricValue"] p{
  font-family:var(--pa-display) !important; font-size:1.02rem !important;
  font-weight:600; color:#EAF6FF !important; margin:.2rem 0 0;
}

/* ===================== EXEMPLOS ===================== */
.pa-exemplos-rot{
  font-size:.62rem; letter-spacing:.17em; text-transform:uppercase;
  font-weight:700; color:var(--pa-suave-2); margin:.4rem 0 .75rem;
}

/* ===================== EXPANDER ===================== */
[data-testid="stExpander"] > details{
  background:rgba(12,29,46,.58); border:1px solid var(--pa-linha);
  border-radius:14px; padding:.1rem .95rem; margin-top:.9rem;
}
[data-testid="stExpander"] summary{ padding:.72rem 0; }
[data-testid="stExpander"] summary p{
  font-size:.68rem !important; letter-spacing:.11em; text-transform:uppercase;
  font-weight:700; color:var(--pa-suave) !important; margin:0;
}
[data-testid="stExpander"] summary [data-testid="stIconMaterial"]{
  color:var(--pa-ciano) !important; transition:transform .2s ease;
}
[data-testid="stExpander"] details[open]{
  border-color:rgba(56,189,248,.34);
  background:rgba(12,29,46,.8);
}
[data-testid="stExpander"] details[open] summary [data-testid="stIconMaterial"]{ transform:rotate(90deg); }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p{
  font-size:.88rem !important; color:var(--pa-suave) !important;
}

/* ===================== ALERTAS ===================== */
[data-testid="stAlert"]{
  border-radius:14px !important; border:1px solid !important;
  background:rgba(251,191,36,.10) !important;
}
[data-testid="stException"]{
  border-radius:14px !important; background:rgba(248,113,113,.10) !important;
  border:1px solid rgba(248,113,113,.4) !important;
}

/* ===================== BOTÕES ===================== */
button[data-testid="stBaseButton-secondary"]{
  background:rgba(18,41,63,.75) !important;
  border:1px solid var(--pa-linha) !important;
  color:var(--pa-texto) !important;
  border-radius:999px !important;
  font-weight:600 !important; font-size:.86rem !important;
  min-height:2.6rem; transition:all .18s ease;
}
button[data-testid="stBaseButton-secondary"]:hover{
  border-color:rgba(56,189,248,.58) !important;
  background:rgba(56,189,248,.13) !important;
  color:#D6EFFF !important;
  transform:translateY(-1px);
}
button[data-testid="stBaseButton-secondary"]:active{ transform:translateY(0); }

a[data-testid="stLinkButton"]{
  background:rgba(56,189,248,.10) !important;
  border:1px solid rgba(56,189,248,.34) !important;
  color:#9BE1FF !important; border-radius:999px !important;
  font-weight:600 !important; font-size:.86rem !important;
  transition:all .18s ease;
}
a[data-testid="stLinkButton"]:hover{
  background:rgba(56,189,248,.2) !important; color:#DCF4FF !important;
  border-color:rgba(56,189,248,.6) !important;
}

/* chips de exemplo moram dentro de colunas */
[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"],
[data-testid="stHorizontalBlock"] > div button[data-testid="stBaseButton-secondary"]{
  background:rgba(11,26,42,.55) !important;
  border:1px dashed rgba(148,197,230,.32) !important;
  color:var(--pa-suave) !important;
  font-size:.79rem !important; font-weight:500 !important;
  text-align:left; line-height:1.38; border-radius:16px !important;
}
[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stHorizontalBlock"] > div button[data-testid="stBaseButton-secondary"]:hover{
  border-style:solid !important;
  border-color:rgba(56,189,248,.58) !important;
  background:rgba(56,189,248,.11) !important;
  color:#EAF6FF !important;
}

/* ===================== CAMPO DE DIGITAÇÃO ===================== */
[data-testid="stBottom"]{
  background:linear-gradient(180deg, rgba(6,15,26,0) 0%, rgba(6,15,26,.88) 44%, #060F1A 100%) !important;
  padding-top:2.4rem !important;
}
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div:first-child{
  background:rgba(11,26,42,.94) !important;
  border:1px solid rgba(56,189,248,.28) !important;
  border-radius:22px !important;
  box-shadow:0 0 0 4px rgba(56,189,248,.05), 0 26px 56px -34px rgba(0,0,0,1) !important;
  backdrop-filter:blur(10px);
}
[data-testid="stChatInput"]:focus-within,
[data-testid="stChatInput"]:focus-within > div:first-child{
  border-color:rgba(56,189,248,.78) !important;
  box-shadow:0 0 0 4px rgba(56,189,248,.15), 0 0 50px -14px rgba(56,189,248,.75) !important;
}
[data-testid="stChatInputTextArea"]{
  color:var(--pa-texto) !important;
  font-family:var(--pa-fonte) !important;
  font-size:1.02rem !important;
}
[data-testid="stChatInputTextArea"]::placeholder{ color:#6E88A3 !important; }
button[data-testid="stChatInputSubmitButton"]{
  background:linear-gradient(135deg,#38BDF8,#0EA5E9) !important;
  color:#04121F !important; border:none !important;
  border-radius:16px !important;
  box-shadow:0 10px 24px -12px rgba(56,189,248,.95) !important;
}
button[data-testid="stChatInputSubmitButton"]:hover{ filter:brightness(1.08); }

/* ===================== DIVERSOS ===================== */
[data-testid="stSpinner"] p{
  color:var(--pa-suave) !important; font-weight:500; letter-spacing:.01em;
}
[data-testid="stCaptionContainer"] p,
[data-testid="stMarkdownContainer"] p{ font-size:.86rem; }

::-webkit-scrollbar{ width:11px; height:11px; }
::-webkit-scrollbar-track{ background:transparent; }
::-webkit-scrollbar-thumb{
  background:rgba(56,189,248,.26); border-radius:99px;
  border:3px solid transparent; background-clip:padding-box;
}
::-webkit-scrollbar-thumb:hover{ background:rgba(56,189,248,.52); background-clip:padding-box; }
::selection{ background:rgba(56,189,248,.34); color:#fff; }
</style>
"""

LOGO = """
<svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
  <defs>
    <linearGradient id="paCiano" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7DD3FC"/>
      <stop offset="1" stop-color="#0EA5E9"/>
    </linearGradient>
    <linearGradient id="paAmbar" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FBBF24"/>
      <stop offset="1" stop-color="#F6A83C"/>
    </linearGradient>
  </defs>
  <circle cx="24" cy="24" r="20.5" fill="none"
          stroke="rgba(56,189,248,.34)" stroke-width="1.4"/>
  <path d="M4.5 24 L24 19.2 L43.5 24 L24 28.8 Z" fill="url(#paAmbar)"/>
  <path d="M24 4.5 L28.8 24 L24 43.5 L19.2 24 Z" fill="url(#paCiano)"/>
  <circle cx="24" cy="24" r="3.4" fill="#060F1A"
          stroke="#EAF6FF" stroke-width="1.5"/>
</svg>
"""

ONDAS = """
<svg class="pa-onda" viewBox="0 0 600 140" preserveAspectRatio="none" aria-hidden="true">
  <defs>
    <linearGradient id="paOnda" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38BDF8" stop-opacity=".34"/>
      <stop offset="1" stop-color="#0EA5E9" stop-opacity=".04"/>
    </linearGradient>
  </defs>
  <path d="M0,84 C70,34 130,120 210,72 C290,26 350,112 430,66 C510,22 560,88 600,64 L600,140 L0,140 Z"
        fill="url(#paOnda)"/>
  <path d="M0,104 C80,66 140,136 230,96 C320,58 380,130 470,92 C540,62 575,110 600,96"
        fill="none" stroke="rgba(56,189,248,.30)" stroke-width="1.6"/>
</svg>
"""


def aplicar_tema() -> None:
    """Injeta a folha de estilo do tema. O Streamlit recria os elementos a cada rerun."""
    st.html(CSS)


def marca_lateral() -> None:
    """Bloco de identidade no topo da barra lateral."""
    st.html(
        f"""
        <div class="pa-marca">
          <div class="pa-logo">{LOGO}</div>
          <div>
            <div class="pa-nome">Porto Alfa</div>
            <div class="pa-sub">Agente RAG · LangGraph</div>
          </div>
        </div>
        <div class="pa-regua"></div>
        """
    )


def cabecalho() -> None:
    """Cartão de abertura com a proposta do projeto."""
    st.html(
        f"""
        <div class="pa-hero">
          <div class="pa-eyebrow"><span class="pa-ponto"></span>Agente RAG · Semana 3</div>
          <h1>O que você quer saber sobre o <em>Porto Alfa</em>?</h1>
          <p>Manual de operações, frota e regras de cálculo. Cada resposta
             chega com as fontes consultadas à mostra.</p>
          {ONDAS}
        </div>
        """
    )


def painel_lateral(modelo: str, embeddings: str) -> None:
    """Ficha técnica dos modelos usados, na lateral."""
    st.html(
        f"""
        <div class="pa-info">
          <div class="pa-campo"><b>Modelo</b><span>{escape(modelo)}</span></div>
          <div class="pa-campo"><b>Embeddings</b><span>{escape(embeddings)}</span></div>
        </div>
        """
    )


def linha_fontes(fontes: list[str]) -> str:
    """Chips com os documentos consultados em uma resposta."""
    if not fontes:
        return ""
    chips = "".join(
        f'<span class="pa-chip" title="{escape(f)}">{escape(f)}</span>' for f in fontes
    )
    return f'<div class="pa-fontes"><span class="pa-rot">Fontes</span>{chips}</div>'


def rotulo_exemplos() -> str:
    return '<div class="pa-exemplos-rot">Ou comece por uma destas</div>'


def rodape_lateral() -> None:
    st.html(
        '<div class="pa-rodape">Respostas geradas por LLM com recuperação '
        'aumentada. Confira sempre as fontes antes de agir.</div>'
    )
