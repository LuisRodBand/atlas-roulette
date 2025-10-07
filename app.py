import streamlit as st
import json
import random
from datetime import datetime
from collections import Counter, defaultdict
import requests

# ==================== CONFIGURAÇÕES ====================
class Config:
    TELEGRAM_TOKEN = "7743493295:AAGRszg878ADYuWFbO7rAv_WGifv3xzWxfc"
    TELEGRAM_CHAT_ID = "-1003031355230"
    BANKROLL_INICIAL = 5000
    UNIT_SIZE = 25

# ==================== ESTADO DO APLICATIVO ====================
if 'state' not in st.session_state:
    st.session_state.state = {
        "spins": [],
        "bankroll": Config.BANKROLL_INICIAL,
        "estrategias_ativas": {},
        "historico": []
    }

state = st.session_state.state

# ==================== DADOS DA ROLETA ====================
RED_NUMS = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
BLACK_NUMS = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
ZERO = [0]

def cor_numero(numero):
    if numero == 0: return "🟢"
    return "🔴" if numero in RED_NUMS else "⚫"

# ==================== ESTRATÉGIAS SIMPLIFICADAS ====================
def estrategia_atrasados(ultimos_spins):
    """Foca em números que não saem há mais tempo"""
    if len(ultimos_spins) < 20:
        return []
    
    counts = Counter(ultimos_spins)
    # Pega os 8 números que menos saíram
    mais_atrasados = sorted(counts.items(), key=lambda x: x[1])[:8]
    return [num for num, count in mais_atrasados]

def estrategia_cavalos(ultimos_spins):
    """Analisa os últimos dígitos (cavalos)"""
    if len(ultimos_spins) < 15:
        return []
    
    ultimo_numero = ultimos_spins[-1]
    cavalo = ultimo_numero % 10
    
    # Números com mesmo cavalo
    numeros_mesmo_cavalo = [n for n in range(37) if n % 10 == cavalo]
    return numeros_mesmo_cavalo[:6]

def estrategia_cores(ultimos_spins):
    """Analisa sequência de cores"""
    if len(ultimos_spins) < 10:
        return []
    
    ultimas_cores = [cor_numero(n) for n in ultimos_spins[-5:]]
    
    # Se teve 3 cores iguais seguidas, aposta no oposto
    if len(set(ultimas_cores[-3:])) == 1:
        cor_oposta = "🔴" if ultimas_cores[-1] == "⚫" else "⚫"
        if cor_oposta == "🔴":
            return RED_NUMS[:6]
        else:
            return BLACK_NUMS[:6]
    
    return []

# ==================== INTERFACE ====================
st.set_page_config(page_title="ATLAS ROULETTE", layout="centered")

st.markdown("""
<style>
    .main { background: #0f172a; color: white; }
    .stButton>button { 
        background: #10b981; 
        color: white; 
        border: none; 
        padding: 15px 30px; 
        border-radius: 10px; 
        font-size: 18px; 
        font-weight: bold;
        width: 100%;
    }
    .numero-verde { background: #10b981; padding: 10px; border-radius: 8px; margin: 2px; }
    .numero-vermelho { background: #ef4444; padding: 10px; border-radius: 8px; margin: 2px; }
    .numero-preto { background: #1f2937; padding: 10px; border-radius: 8px; margin: 2px; }
    .card { 
        background: rgba(255,255,255,0.1); 
        padding: 20px; 
        border-radius: 15px; 
        margin: 10px 0; 
        border: 1px solid rgba(255,255,255,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ====================
st.markdown("<h1 style='text-align: center; color: #10b981;'>🎯 ATLAS ROULETTE</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Sistema Profissional Simplificado - iPhone Edition</p>", unsafe_allow_html=True)

# ==================== PAINEL PRINCIPAL ====================
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🎲 Registrar Resultado")
    
    numero = st.number_input("Número sorteado (0-36):", min_value=0, max_value=36, step=1)
    
    if st.button("✅ Registrar e Analisar"):
        # Registrar spin
        state["spins"].append(numero)
        
        # Executar estratégias
        estrategias = {
            "📊 Atrasados": estrategia_atrasados(state["spins"]),
            "🐎 Cavalos": estrategia_cavalos(state["spins"]),
            "🎨 Cores": estrategia_cores(state["spins"])
        }
        
        state["estrategias_ativas"] = estrategias
        
        st.success(f"✅ Número {numero} {cor_numero(numero)} registrado!")
        
        # Enviar para Telegram
        try:
            mensagem = f"🎯 ATLAS ROULETTE\n🎲 Último: {numero} {cor_numero(numero)}\n📊 Total: {len(state['spins'])} spins\n\n"
            
            for nome, numeros in estrategias.items():
                if numeros:
                    mensagem += f"{nome}: {', '.join(map(str, numeros))}\n"
            
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
            data = {
                "chat_id": Config.TELEGRAM_CHAT_ID,
                "text": mensagem
            }
            requests.post(url, data=data, timeout=5)
            st.info("📱 Relatório enviado para Telegram!")
        except:
            st.info("💾 Análise salva localmente")
    
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💰 Bankroll")
    st.metric("Saldo", f"R$ {state['bankroll']:,.2f}")
    
    st.subheader("📈 Estatísticas")
    st.write(f"Spins: {len(state['spins'])}")
    if state["spins"]:
        ultimo = state["spins"][-1]
        st.write(f"Último: {ultimo} {cor_numero(ultimo)}")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== ESTRATÉGIAS ATIVAS ====================
if state["estrategias_ativas"]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🎯 Estratégias Ativas")
    
    for nome, numeros in state["estrategias_ativas"].items():
        if numeros:
            st.write(f"**{nome}**")
            cols = st.columns(6)
            for i, num in enumerate(numeros[:6]):
                with cols[i]:
                    cor_classe = "numero-verde" if num == 0 else "numero-vermelho" if num in RED_NUMS else "numero-preto"
                    st.markdown(f"<div class='{cor_classe}' style='text-align: center;'>{num}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== ÚLTIMOS RESULTADOS ====================
if state["spins"]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Últimos Resultados")
    
    ultimos_10 = state["spins"][-10:]
    cols = st.columns(10)
    
    for i, num in enumerate(ultimos_10):
        with cols[i]:
            emoji = cor_numero(num)
            st.markdown(f"<div style='text-align: center; font-size: 20px;'>{emoji}<br><strong>{num}</strong></div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== DICAS RÁPIDAS ====================
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.subheader("💡 Dicas Rápidas")

dicas = [
    "🎯 **Atrasados**: Números que não saem há mais tempo",
    "🐎 **Cavalos**: Números com mesmo último dígito",
    "🎨 **Cores**: Inverte após 3 cores iguais",
    "💰 **Bankroll**: Aposte 1-2% do saldo por rodada"
]

for dica in dicas:
    st.write(dica)

st.markdown("</div>", unsafe_allow_html=True)

# ==================== RODAPÉ ====================
st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>📱 Atlas Roulette - iPhone Edition © 2024</p>", unsafe_allow_html=True)
