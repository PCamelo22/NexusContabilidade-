# email_service.py — ElaConta v1.0

import smtplib
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA     = os.getenv("EMAIL_SENHA")


def gerar_codigo() -> str:
    return ''.join(random.choices(string.digits, k=6))


def _smtp_send(msg: MIMEMultipart, destinatario: str) -> bool:
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("[email_service] EMAIL_REMETENTE ou EMAIL_SENHA não configurados — e-mail ignorado")
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(EMAIL_REMETENTE, EMAIL_SENHA)
            smtp.sendmail(EMAIL_REMETENTE, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"[email_service] Erro ao enviar e-mail: {e}")
        return False


def enviar_codigo(destinatario: str, codigo: str, nome: str = "") -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ElaConta — Seu código de confirmação: {codigo}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = destinatario

    html = f"""
    <html>
    <body style="font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#F5F3FF;padding:40px 20px">
      <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;
                  border:1px solid #EDE9FE;padding:40px">

        <div style="text-align:center;margin-bottom:32px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:56px;height:56px;border-radius:16px;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);
                      margin-bottom:12px">
            <span style="color:white;font-size:24px">▲</span>
          </div>
          <div style="font-size:22px;font-weight:700;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            ElaConta
          </div>
        </div>

        <h2 style="font-size:18px;font-weight:600;color:#1E1B4B;margin-bottom:8px">
          Olá{', ' + nome if nome else ''}! 👋
        </h2>
        <p style="font-size:14px;color:#6B7280;margin-bottom:28px">
          Use o código abaixo para confirmar seu cadastro no ElaConta.
          O código expira em <strong>10 minutos</strong>.
        </p>

        <div style="background:#F5F3FF;border:2px dashed #DDD6FE;border-radius:12px;
                    padding:24px;text-align:center;margin-bottom:28px">
          <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#6B21A8">
            {codigo}
          </div>
        </div>

        <p style="font-size:12px;color:#9CA3AF;text-align:center">
          Se você não solicitou este código, ignore este e-mail.
        </p>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))
    return _smtp_send(msg, destinatario)


def enviar_recuperacao(destinatario: str, codigo: str, nome: str = "") -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ElaConta — Código para redefinir senha: {codigo}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = destinatario

    html = f"""
    <html>
    <body style="font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#F5F3FF;padding:40px 20px">
      <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;
                  border:1px solid #EDE9FE;padding:40px">

        <div style="text-align:center;margin-bottom:32px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:56px;height:56px;border-radius:16px;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);margin-bottom:12px">
            <span style="color:white;font-size:24px">🔑</span>
          </div>
          <div style="font-size:22px;font-weight:700;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            ElaConta
          </div>
        </div>

        <h2 style="font-size:18px;font-weight:600;color:#1E1B4B;margin-bottom:8px">
          Redefinição de senha{', ' + nome if nome else ''}
        </h2>
        <p style="font-size:14px;color:#6B7280;margin-bottom:28px">
          Use o código abaixo para criar uma nova senha.
          O código expira em <strong>10 minutos</strong>.
        </p>

        <div style="background:#F5F3FF;border:2px dashed #DDD6FE;border-radius:12px;
                    padding:24px;text-align:center;margin-bottom:28px">
          <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#6B21A8">
            {codigo}
          </div>
        </div>

        <p style="font-size:12px;color:#9CA3AF;text-align:center">
          Se você não solicitou a redefinição de senha, ignore este e-mail.
          Sua senha atual permanece inalterada.
        </p>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))
    return _smtp_send(msg, destinatario)


def enviar_nova_conta(destinatario: str, nome_empresa: str,
                      descricao: str, valor: float, vencimento: str,
                      codigo_barras: str = None, arquivo_url: str = None,
                      base_url: str = "http://localhost:8000") -> bool:
    """Notifica o cliente que a contadora lançou uma nova cobrança."""
    from datetime import datetime
    try:
        dt   = datetime.strptime(vencimento, "%Y-%m-%d")
        venc = dt.strftime("%d/%m/%Y")
    except Exception:
        venc = vencimento

    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    barras_bloco = ""
    if codigo_barras:
        barras_bloco = f"""
        <div style="background:#F5F3FF;border-radius:8px;padding:12px 16px;margin-top:12px;
                    word-break:break-all;font-family:monospace;font-size:12px;color:#6B21A8">
          <div style="font-size:11px;color:#6B7280;font-family:sans-serif;
                      margin-bottom:4px">Código de barras</div>
          {codigo_barras}
        </div>"""

    boleto_bloco = ""
    if arquivo_url:
        url = f"{base_url}{arquivo_url}"
        boleto_bloco = f"""
        <div style="text-align:center;margin-top:20px">
          <a href="{url}"
             style="display:inline-block;padding:12px 28px;border-radius:10px;
             background:linear-gradient(135deg,#6B21A8,#EC1E8C);color:#fff;
             font-weight:600;text-decoration:none;font-size:14px">
            📄 Baixar Boleto
          </a>
        </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ElaConta — Nova cobrança: {descricao} · {venc}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = destinatario

    html = f"""
    <html>
    <body style="font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#F5F3FF;padding:40px 20px">
      <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;
                  border:1px solid #EDE9FE;padding:40px">

        <div style="text-align:center;margin-bottom:28px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:56px;height:56px;border-radius:16px;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);margin-bottom:12px">
            <span style="color:white;font-size:24px">💳</span>
          </div>
          <div style="font-size:22px;font-weight:700;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            ElaConta
          </div>
        </div>

        <h2 style="font-size:18px;font-weight:600;color:#1E1B4B;margin-bottom:6px">
          Nova cobrança disponível 📬
        </h2>
        <p style="font-size:14px;color:#6B7280;margin-bottom:24px">
          Sua contadora adicionou uma nova cobrança para <strong>{nome_empresa}</strong>.
        </p>

        <div style="background:#F5F3FF;border-radius:12px;padding:20px;margin-bottom:8px">
          <table style="width:100%;border-collapse:collapse;font-size:14px">
            <tr>
              <td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #EDE9FE">Descrição</td>
              <td style="padding:8px 0;font-weight:600;color:#1E1B4B;border-bottom:1px solid #EDE9FE;text-align:right">{descricao}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #EDE9FE">Valor</td>
              <td style="padding:8px 0;font-weight:700;color:#6B21A8;border-bottom:1px solid #EDE9FE;text-align:right;font-size:18px">{valor_fmt}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#6B7280">Vencimento</td>
              <td style="padding:8px 0;font-weight:600;color:#EF4444;text-align:right">{venc}</td>
            </tr>
          </table>
          {barras_bloco}
        </div>

        {boleto_bloco}

        <div style="text-align:center;margin-top:24px">
          <a href="{base_url}/cliente"
             style="display:inline-block;padding:11px 24px;border-radius:10px;
             border:1px solid #DDD6FE;color:#6B21A8;
             font-weight:600;text-decoration:none;font-size:13px">
            Acessar o ElaConta →
          </a>
        </div>

        <p style="font-size:12px;color:#9CA3AF;text-align:center;margin-top:24px">
          Acesse o sistema para pagar e enviar o comprovante.
        </p>
      </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))
    return _smtp_send(msg, destinatario)


def enviar_boleto_disponivel(destinatario: str, nome_empresa: str,
                              descricao: str, valor: float, vencimento: str,
                              arquivo_url: str, base_url: str = "http://localhost:8000") -> bool:
    """Notifica o cliente que o boleto PDF foi anexado."""
    from datetime import datetime
    try:
        venc = datetime.strptime(vencimento, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        venc = vencimento

    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    url_boleto = f"{base_url}{arquivo_url}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ElaConta — Boleto disponível: {descricao}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = destinatario

    html = f"""
    <html>
    <body style="font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#F5F3FF;padding:40px 20px">
      <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;
                  border:1px solid #EDE9FE;padding:40px">

        <div style="text-align:center;margin-bottom:28px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:56px;height:56px;border-radius:16px;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);margin-bottom:12px">
            <span style="color:white;font-size:24px">📄</span>
          </div>
          <div style="font-size:22px;font-weight:700;
                      background:linear-gradient(135deg,#6B21A8,#EC1E8C);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            ElaConta
          </div>
        </div>

        <h2 style="font-size:18px;font-weight:600;color:#1E1B4B;margin-bottom:6px">
          Boleto disponível para download 📎
        </h2>
        <p style="font-size:14px;color:#6B7280;margin-bottom:24px">
          O boleto de <strong>{descricao}</strong> ({valor_fmt}) com vencimento em
          <strong>{venc}</strong> está pronto para download.
        </p>

        <div style="text-align:center;margin:28px 0">
          <a href="{url_boleto}"
             style="display:inline-block;padding:14px 32px;border-radius:10px;
             background:linear-gradient(135deg,#6B21A8,#EC1E8C);color:#fff;
             font-weight:700;text-decoration:none;font-size:15px">
            📄 Baixar Boleto
          </a>
        </div>

        <p style="font-size:12px;color:#9CA3AF;text-align:center">
          Acesse o <a href="{base_url}/cliente" style="color:#6B21A8">ElaConta</a>
          para enviar o comprovante após o pagamento.
        </p>
      </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))
    return _smtp_send(msg, destinatario)


def enviar_solicitacao(dados) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ElaConta — Nova solicitação: {dados.nome}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = EMAIL_REMETENTE

    mensagem_bloco = (
        f'<div style="margin-top:20px;padding:16px;background:#F5F3FF;border-radius:8px;font-size:13px">'
        f'<strong>Mensagem:</strong><br>{dados.mensagem}</div>'
        if dados.mensagem else ""
    )

    html = f"""
    <html>
    <body style="font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#F5F3FF;padding:40px 20px">
      <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
                  border:1px solid #EDE9FE;padding:40px">
        <div style="text-align:center;margin-bottom:28px">
          <div style="font-size:22px;font-weight:700;
            background:linear-gradient(135deg,#6B21A8,#EC1E8C);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            ElaConta
          </div>
          <div style="font-size:13px;color:#6B7280;margin-top:4px">Nova solicitação de contato</div>
        </div>

        <div style="background:#F5F3FF;border-radius:12px;padding:20px;margin-bottom:20px">
          <div style="font-size:18px;font-weight:700;color:#1E1B4B;margin-bottom:4px">{dados.nome}</div>
          <div style="font-size:13px;color:#6B7280">{dados.email} · {dados.telefone}</div>
        </div>

        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <tr><td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #EDE9FE">CNPJ</td>
              <td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE9FE">{dados.cnpj or '—'}</td></tr>
          <tr><td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #EDE9FE">Segmento</td>
              <td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE9FE">{dados.segmento}</td></tr>
          <tr><td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #EDE9FE">Porte</td>
              <td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE9FE">{dados.porte}</td></tr>
          <tr><td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #EDE9FE">Faturamento</td>
              <td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE9FE">{dados.faturamento}</td></tr>
          <tr><td style="padding:8px 0;color:#6B7280">Honorário sugerido</td>
              <td style="padding:8px 0;font-weight:700;color:#6B21A8">{dados.honorario or '—'}</td></tr>
        </table>

        {mensagem_bloco}

        <div style="margin-top:24px;text-align:center">
          <a href="https://wa.me/5561982955839?text=Olá! Vi sua solicitação no ElaConta."
             style="display:inline-block;padding:12px 24px;border-radius:10px;
             background:linear-gradient(135deg,#6B21A8,#EC1E8C);color:#fff;
             font-weight:600;text-decoration:none;font-size:14px">
            Responder via WhatsApp
          </a>
        </div>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))
    return _smtp_send(msg, EMAIL_REMETENTE)
