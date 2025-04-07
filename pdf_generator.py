from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
import datetime
import locale
import backup_drive

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
    
    # Generar número único basado en fecha y hora
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(pdf_dir, f"cotizacion_{cotizacion.id}_{timestamp}.pdf")
    
    # Configure the document
    doc = SimpleDocTemplate(filename, pagesize=letter)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    
    # Header with logo and company info (top of document)
    logo_path = os.path.join('static', 'img', 'logo.png')
    
    # Create a table for the header (logo + company info)
    header_data = [[]]
    
    # First column: Logo
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 0.75 * inch
        logo.drawWidth = 0.75 * inch
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
    header_table = Table(header_data, colWidths=[1*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Title
    title = Paragraph(f"<font size='14'><b>QUOTE #{cotizacion.id}</b></font>", styles['Center'])
    elements.append(title)
    elements.append(Spacer(1, 0.15*inch))
    
    # Client information
    data = [
        ["CLIENT INFORMATION"],
        [f"Name: {cotizacion.cliente.nombre}"],
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
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
        ('BACKGROUND', (0, 1), (0, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.15*inch))
    
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
    elements.append(Spacer(1, 0.15*inch))
    
    # Quote description
    if cotizacion.descripcion:
        elements.append(Paragraph("<b>Description:</b>", styles['Normal']))
        elements.append(Paragraph(cotizacion.descripcion, styles['Normal']))
        elements.append(Spacer(1, 0.15*inch))
    
    # Quote items
    elements.append(Paragraph("<b>Quote Details:</b>", styles['Normal']))
    
    # Item table header
    items_data = [['Item', 'Qty', 'Unit Price', 'Subtotal']]
    
    # Add items
    for item in cotizacion.items:
        items_data.append([
            item.nombre,
            str(item.cantidad),
            format_currency(item.precio_unitario),
            format_currency(item.subtotal)
        ])
    
    # Add totals
    items_data.append(['', '', 'Subtotal:', format_currency(cotizacion.subtotal)])
    tax_rate = 0.07  # 7% tax rate
    tax_amount = cotizacion.subtotal * tax_rate
    total = cotizacion.subtotal + tax_amount
    items_data.append(['', '', f'Tax ({int(tax_rate*100)}%):', format_currency(tax_amount)])
    items_data.append(['', '', 'TOTAL:', format_currency(total)])
    
    # Create items table
    items_table = Table(items_data, colWidths=[doc.width*0.4, doc.width*0.1, doc.width*0.25, doc.width*0.25])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, -3), (2, -1), 'Helvetica-Bold'),  # Make totals bold
        ('BOTTOMPADDING', (0, 0), (3, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (2, -3), (3, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    
    # Final notes
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph("<b>Terms and Conditions:</b>", styles['Normal']))
    elements.append(Paragraph("1. This quote is valid until the date specified above.", styles['Normal']))
    elements.append(Paragraph("2. Prices may change without notice after the expiration date.", styles['Normal']))
    elements.append(Paragraph("3. Payment methods: Zell transfer, or credit card.", styles['Normal']))
    elements.append(Paragraph("4. A 30% deposit is required prior to the start of the project.", styles['Normal']))
    elements.append(Paragraph("   A 40% progress payment will be due once the project is halfway completed.", styles['Normal']))
    elements.append(Paragraph("   The remaining 30% is due upon project completion and final approval.", styles['Normal']))
    # Add signature spaces
    elements.append(Spacer(1, 0.5*inch))
    
    # Create signature table
    signature_data = [
        ["_______________________", "_______________________"],
        ["Client", "WNL FLOORING"],
        ["", ""],
        ["Date", "Date"]
    ]
    
    signature_table = Table(signature_data, colWidths=[doc.width/2.0, doc.width/2.0])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
    ]))
    elements.append(signature_table)
    
    # Generate PDF
    doc.build(elements)
    
    # Subir solo este PDF a Google Drive
    try:
        import logging
        success, message = backup_drive.subir_pdf_cotizacion(filename)
        if not success:
            logging.error(f"Error al subir cotización a Drive: {message}")
    except Exception as e:
        import logging
        logging.error(f"Error al subir cotización a Drive: {str(e)}")
    
    return os.path.basename(filename)

def generar_pdf_factura(factura):
    # Create directory for PDFs if it doesn't exist
    pdf_dir = os.path.join('static', 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Generar número único basado en fecha y hora
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(pdf_dir, f"factura_{factura.id}_{timestamp}.pdf")
    
    # Configure the document
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
    title = Paragraph(f"<font size='16'><b>INVOICE #{factura.numero_factura}</b></font>", styles['Center'])
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))
    
    # Client information
    data = [
        ["CLIENT INFORMATION"],
        [f"Name: {factura.cliente.nombre}"],
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
    items_data.append(['', '', 'Subtotal:', format_currency(factura.subtotal)])
    # Using 7% tax rate
    tax_rate = 0.07
    tax_amount = factura.subtotal * tax_rate
    total = factura.subtotal + tax_amount
    items_data.append(['', '', f'Tax ({int(tax_rate*100)}%):', format_currency(tax_amount)])
    items_data.append(['', '', 'TOTAL:', format_currency(total)])
    
    # Create items table
    items_table = Table(items_data, colWidths=[doc.width*0.4, doc.width*0.1, doc.width*0.25, doc.width*0.25])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, -3), (2, -1), 'Helvetica-Bold'),  # Make totals bold
        ('BOTTOMPADDING', (0, 0), (3, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (2, -3), (3, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    
    # Payment status
    if factura.pagada:
        status_text = f"<b>Payment Status:</b> <font color='green'><b>PAID</b></font> - Payment Date: {factura.fecha_pago.strftime('%m/%d/%Y')}"
    else:
        status_text = f"<b>Payment Status:</b> <font color='red'><b>UNPAID</b></font>"
    
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph(status_text, styles['Normal']))
    
    # Final notes
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("<b>Payment Instructions:</b>", styles['Normal']))
    elements.append(Paragraph("1. Please make payment within the specified due date.", styles['Normal']))
    elements.append(Paragraph("2. Payment methods: Zelle payment, check, or credit card.", styles['Normal']))
    elements.append(Paragraph("3. Please include the invoice number in your payment reference.", styles['Normal']))
    
    # Add signature spaces
    elements.append(Spacer(1, 1*inch))
    
    # Create signature table
    signature_data = [
        ["_______________________", "_______________________"],
        ["Client", "WNL FLOORING"],
        ["", ""],
        ["Date", "Date"]
    ]
    
    signature_table = Table(signature_data, colWidths=[doc.width/2.0, doc.width/2.0])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
    ]))
    elements.append(signature_table)
    
    # Generate PDF
    doc.build(elements)
    
    # Subir solo este PDF a Google Drive
    try:
        import logging
        success, message = backup_drive.subir_pdf_factura(filename)
        if not success:
            logging.error(f"Error al subir factura a Drive: {message}")
    except Exception as e:
        import logging
        logging.error(f"Error al subir factura a Drive: {str(e)}")
    
    return os.path.basename(filename)