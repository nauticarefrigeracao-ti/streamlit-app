"""
Classificação de produtos em 5 status operacionais.
Usa medianas do período como thresholds — relativo ao portfólio atual.

Status:
  Estrela      — alta receita + alta margem  → proteger estoque
  Volume Cego  — alta receita + baixa margem → revisar precificação
  Oportunidade — baixa receita + alta margem → ativar em campanha
  Parado       — baixa receita + baixa margem → avaliar descontinuação
  Problema     — margem negativa (qualquer volume) → ação urgente
"""

import pandas as pd

STATUS_COLORS = {
    "Estrela":      "#1F7A3A",
    "Volume Cego":  "#C8901C",
    "Oportunidade": "#2E6FA8",
    "Parado":       "#9BACBD",
    "Problema":     "#B5322B",
}

STATUS_ICONS = {
    "Estrela":      "★",
    "Volume Cego":  "⚠",
    "Oportunidade": "↑",
    "Parado":       "◯",
    "Problema":     "✕",
}

STATUS_DESC = {
    "Estrela":      "Alta receita + alta margem. Proteger estoque, nunca faltar.",
    "Volume Cego":  "Alta receita + baixa margem. Revise precificação ou negocie custo.",
    "Oportunidade": "Baixa receita + alta margem. Ative em campanha ou promoção.",
    "Parado":       "Baixo volume + baixa margem. Avalie descontinuação.",
    "Problema":     "Margem negativa. Ação urgente — empresa perde dinheiro nesse produto.",
}

STATUS_TOOLTIP = {
    "Estrela": (
        "O melhor cenário possível: vende bem E tem margem saudável. "
        "Esses produtos pagam as contas e geram lucro real. "
        "Prioridade máxima: nunca deixe o estoque zerar — uma ruptura aqui é dinheiro direto no lixo. "
        "Negocie volume com o fornecedor para defender ou melhorar a margem."
    ),
    "Volume Cego": (
        "Esse produto fatura muito, mas boa parte do dinheiro some antes de chegar no caixa. "
        "Alta receita com margem baixa significa que você está trabalhando muito para lucrar pouco. "
        "Ação: revise o preço de venda ou negocie o custo com o fornecedor. "
        "Uma melhora de 2–3 pontos percentuais na margem aqui tem grande impacto no lucro total."
    ),
    "Oportunidade": (
        "Produto lucrativo que ainda não ganhou tração de vendas. "
        "A margem está acima da média do portfólio — cada venda rende bem. "
        "O problema é o volume baixo. "
        "Ação: teste uma campanha, melhore o anúncio ou ofereça frete grátis. "
        "Se o volume crescer, esse produto pode virar uma Estrela."
    ),
    "Parado": (
        "Pouco volume e margem baixa — o pior dos dois mundos. "
        "Esse produto ocupa capital de giro, espaço no estoque e atenção operacional sem retorno proporcional. "
        "Avalie descontinuação: se não há perspectiva de melhora no volume ou na margem, "
        "cortar esse produto libera recursos para os que realmente performam."
    ),
    "Problema": (
        "Cada venda desse produto gera prejuízo — o custo total supera o que ele rende. "
        "Manter no portfólio ativo significa pagar para vender. "
        "Ação imediata: suspender anúncios, revisar precificação ou descontinuar. "
        "Quanto mais vender, mais dinheiro perde. Não existe volume que resolva margem negativa."
    ),
}


def classificar(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna 'status' ao DataFrame de vendas."""
    df = df.copy()
    med_receita = df["receita_total"].median()
    med_margem  = df[df["margem"] >= 0]["margem"].median()  # só positivos pra threshold

    def _status(row) -> str:
        if row["margem"] < 0:
            return "Problema"
        alta_r = row["receita_total"] >= med_receita
        alta_m = row["margem"] >= med_margem
        if alta_r and alta_m:
            return "Estrela"
        if alta_r:
            return "Volume Cego"
        if alta_m:
            return "Oportunidade"
        return "Parado"

    df["status"] = df.apply(_status, axis=1)
    return df


def resumo_classificacao(df: pd.DataFrame) -> pd.DataFrame:
    """Contagem e receita por status."""
    return (
        df.groupby("status")
        .agg(qtd=("sku", "count"), receita=("receita_total", "sum"),
             margem_media=("margem", "mean"))
        .reset_index()
        .sort_values("receita", ascending=False)
    )
