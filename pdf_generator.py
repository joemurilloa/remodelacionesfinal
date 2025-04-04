from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from datetime import datetime
import locale

# Configure locale for US format
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    pass  # If it fails, we'll use the default locale

def format_currency(value):
    return f"${value:,.2f}"

def generar_pdf_cotizacion(cotizacion):
    # Create directory for PDFs if it doesn't exist
    pdf_dir = os.path.join('static', 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Configure the document
    filename = os.path.join(pdf_dir, f"cotizacion_{cotizacion.id}.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    
    # Header with logo and company info (top of document)
    # Logo is placed to the left, company info to the right
    logo_path = os.path.join('static', 'img', 'logo.png')
    
    # Create a table for the header (logo + company info)
    header_data = [[]]
    
    # First column: Logo
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        # Make logo circular by setting equal dimensions
        logo.drawHeight = 1 * inch
        logo.drawWidth = 1 * inch
        header_data[0].append(logo)
    else:
        header_data[0].append("")
    
    # Second column: Company info
    company_info = """
    <font size="12"><b>WNL FLOORING</b></font><br/>
    Phone: (786) 762-6304<br/>
    Email: wnlflooring@gmail.com<br/>
    Web: https://wnlflooring.netlify.app/
    """
    header_data[0].append(Paragraph(company_info, styles['Normal']))
    
    # Create the header table
    header_table = Table(header_data, colWidths=[1.5*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Title
    title = Paragraph(f"<font size='16'><b>QUOTE #{cotizacion.id}</b></font>", styles['Center'])
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))
    
    # Client information
    data = [
        ["CLIENT INFORMATION"],
        [f"Name: {cotizacion.cliente.nombre}"],
        [f"Tax ID: {cotizacion.cliente.rut or 'Not specified'}"],
        [f"Address: {cotizacion.cliente.direccion or 'Not specified'}"],
        [f"Phone: {cotizacion.cliente.telefono or 'Not specified'}"],
        [f"Email: {cotizacion.cliente.email or 'Not specified'}"]
    ]
    
    # Create data table
    info_table = Table(data, colWidths=[doc.width])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.black),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ('BACKGROUND', (0, 1), (0, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Date and validity
    fecha_formato = cotizacion.fecha.strftime("%m/%d/%Y")
    fecha_vencimiento = cotizacion.fecha_vencimiento.strftime("%m/%d/%Y")
    
    fecha_info = [
        ["Issue Date:", fecha_formato],
        ["Valid Until:", fecha_vencimiento]
    ]
    
    fecha_table = Table(fecha_info, colWidths=[doc.width/4.0, doc.width/4.0])
    fecha_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(fecha_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Quote description
    if cotizacion.descripcion:
        elements.append(Paragraph("<b>Description:</b>", styles['Normal']))
        elements.append(Paragraph(cotizacion.descripcion, styles['Normal']))
        elements.append(Spacer(1, 0.25*inch))
    
    # Quote items
    elements.append(Paragraph("<b>Quote Details:</b>", styles['Normal']))
    
    # Item table header
    items_data = [['Item', 'Quantity', 'Unit Price', 'Subtotal']]
    
    # Add items
    for item in cotizacion.items:
        items_data.append([
            item.nombre,
            str(item.cantidad),
            format_currency(item.precio_unitario),
            format_currency(item.subtotal)
        ])
    
    # Add totals
    items_data.append(['', '', '<b>Subtotal:</b>', format_currency(cotizacion.subtotal)])
    # Using Chilean tax rate
    tax_rate = 0.19  # 19% IVA en Chile
    tax_amount = cotizacion.subtotal * tax_rate
    total = cotizacion.subtotal + tax_amount
    items_data.append(['', '', f'<b>IVA ({int(tax_rate*100)}%):</b>', format_currency(tax_amount)])
    items_data.append(['', '', '<b>TOTAL:</b>', format_currency(total)])
    
    # Create items table
    items_table = Table(items_data, colWidths=[doc.width*0.4, doc.width*0.1, doc.width*0.25, doc.width*0.25])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (3, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (2, -3), (3, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    
    # Final notes
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("<b>Terms and Conditions:</b>", styles['Normal']))
    elements.append(Paragraph("1. This quote is valid until the date specified above.", styles['Normal']))
    elements.append(Paragraph("2. Prices may change without notice after the expiration date.", styles['Normal']))
    elements.append(Paragraph("3. Payment methods: Bank transfer, check, or credit card.", styles['Normal']))
    elements.append(Paragraph("4. 50% deposit required to start the project.", styles['Normal']))
    elements.append(Paragraph("5. Full payment is due upon completion of the work.", styles['Normal']))
    
    # Generate PDF
    doc.build(elements)
    
    # Sincronizar PDFs de cotizaciones con Google Drive
    try:
        import logging
        import backup_drive
        success, message = backup_drive.sincronizar_pdfs_cotizaciones()
        if not success:
            logging.error(f"Error al sincronizar cotizaciones con Drive: {message}")
    except Exception as e:
        import logging
        logging.error(f"Error al sincronizar cotizaciones con Drive: {str(e)}")
    
    return f"cotizacion_{cotizacion.id}.pdf"

def generar_pdf_factura(factura):
    # Create directory for PDFs if it doesn't exist
    pdf_dir = os.path.join('static', 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Configure the document
    filename = os.path.join(pdf_dir, f"factura_{factura.id}.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    
    # Header with logo and company info (top of document)
    # Logo is placed to the left, company info to the right
    logo_path = os.path.join('static', 'img', 'logo.png')
    
    # Create a table for the header (logo + company info)
    header_data = [[]]
    
    # First column: Logo
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        # Make logo circular by setting equal dimensions
        logo.drawHeight = 1 * inch
        logo.drawWidth = 1 * inch
        header_data[0].append(logo)
    else:
        header_data[0].append("")
    
    # Second column: Company info
    company_info = """
    <font size="12"><b>WNL FLOORING</b></font><br/>
    Phone: (786) 762-6304<br/>
    Email: wnlflooring@gmail.com<br/>
    Web: https://wnlflooring.netlify.app/
    """
    header_data[0].append(Paragraph(company_info, styles['Normal']))
    
    # Create the header table
    header_table = Table(header_data, colWidths=[1.5*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Title
    title = Paragraph(f"<font size='16'><b>INVOICE #{factura.id}</b></font>", styles['Center'])
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))
    
    # Client information
    data = [
        ["CLIENT INFORMATION"],
        [f"Name: {factura.cliente.nombre}"],
        [f"Tax ID: {factura.cliente.rut or 'Not specified'}"],
        [f"Address: {factura.cliente.direccion or 'Not specified'}"],
        [f"Phone: {factura.cliente.telefono or 'Not specified'}"],
        [f"Email: {factura.cliente.email or 'Not specified'}"]
    ]
    
    # Create data table
    info_table = Table(data, colWidths=[doc.width])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.black),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ('BACKGROUND', (0, 1), (0, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Date and related quote information
    fecha_formato = factura.fecha.strftime("%m/%d/%Y")
    
    fecha_info = [
        ["Issue Date:", fecha_formato],
    ]
    
    if factura.cotizacion:
        fecha_info.append(["Based on Quote:", f"#{factura.cotizacion.id}"])
    
    fecha_table = Table(fecha_info, colWidths=[doc.width/4.0, doc.width/4.0])
    fecha_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(fecha_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Invoice description
    if factura.descripcion:
        elements.append(Paragraph("<b>Description:</b>", styles['Normal']))
        elements.append(Paragraph(factura.descripcion, styles['Normal']))
        elements.append(Spacer(1, 0.25*inch))
    
    # Invoice items
    elements.append(Paragraph("<b>Invoice Details:</b>", styles['Normal']))
    
    # Header for items table
    items_data = [['Item', 'Quantity', 'Unit Price', 'Subtotal']]
    
    # Add items
    for item in factura.items:
        items_data.append([
            item.nombre,
            str(item.cantidad),
            format_currency(item.precio_unitario),
            format_currency(item.subtotal)
        ])
    
    # Add totals
    items_data.append(['', '', '<b>Subtotal:</b>', format_currency(factura.subtotal)])
    # Using Chilean tax rate
    tax_rate = 0.19  # 19% IVA en Chile
    tax_amount = factura.subtotal * tax_rate
    total = factura.subtotal + tax_amount
    items_data.append(['', '', f'<b>IVA ({int(tax_rate*100)}%):</b>', format_currency(tax_amount)])
    items_data.append(['', '', '<b>TOTAL:</b>', format_currency(total)])
    
    # Create items table
    items_table = Table(items_data, colWidths=[doc.width*0.4, doc.width*0.1, doc.width*0.25, doc.width*0.25])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (3, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (2, -3), (3, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    
    # Payment status
    elements.append(Spacer(1, 0.25*inch))
    estado_pago = "PAID" if factura.pagada else "PENDING PAYMENT"
    estado_style = 'Heading2'
    estado_color = colors.green if factura.pagada else colors.red
    
    estado_paragraph = Paragraph(f"<font color={estado_color}><b>{estado_pago}</b></font>", styles[estado_style])
    elements.append(estado_paragraph)
    
    # Payment information
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph("<b>Payment Information:</b>", styles['Normal']))
    elements.append(Paragraph("Bank: Chase Bank", styles['Normal']))
    elements.append(Paragraph("Account Type: Business Checking", styles['Normal']))
    elements.append(Paragraph("Account Number: XXX-XXXX-XXX", styles['Normal']))
    elements.append(Paragraph("Routing Number: XXXXXXXX", styles['Normal']))
    elements.append(Paragraph("Account Name: WNL FLOORING LLC", styles['Normal']))
    elements.append(Paragraph("Email: wnlflooring@gmail.com", styles['Normal']))
    
    # Final notes
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph("<b>Notes:</b>", styles['Normal']))
    elements.append(Paragraph("1. Please include the invoice number in your payment reference.", styles['Normal']))
    elements.append(Paragraph("2. Payment is due within 15 days of invoice date.", styles['Normal']))
    elements.append(Paragraph("3. For questions regarding this invoice, please contact us at (786) 762-6304.", styles['Normal']))
    
    # Generate PDF
    doc.build(elements)
    
    # Sincronizar PDFs de facturas con Google Drive
    try:
        import logging
        import backup_drive
        success, message = backup_drive.sincronizar_pdfs_facturas()
        if not success:
            logging.error(f"Error al sincronizar facturas con Drive: {message}")
    except Exception as e:
        import logging
        logging.error(f"Error al sincronizar facturas con Drive: {str(e)}")
    
    return f"factura_{factura.id}.pdf"