package com.protrack.app.domain.export

import java.io.ByteArrayOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** فهارس أنماط الخلايا في styles.xml — ثابتة ومتطابقة مع ترتيب XFS. */
object XlsxStyle {
    const val DEFAULT = 0
    const val TITLE = 1
    const val SECTION = 2
    const val LABEL = 3
    const val VALUE = 4
    const val HEADER = 5
    const val CELL = 6
    const val CELL_CENTER = 7
    const val OK = 8
    const val MINOR = 9
    const val FAULT = 10
    const val FOOTER = 11
    const val BOLD_VALUE = 12
    const val CELL_NUM = 13
}

data class XlsxCell(val value: Any?, val style: Int = XlsxStyle.DEFAULT)

data class XlsxRow(val cells: List<XlsxCell>, val height: Double? = null)

/** شيت كامل: صفوف + عرض أعمدة + دمج + RTL + إخفاء. */
data class XlsxSheet(
    val name: String,
    val rows: List<XlsxRow>,
    val colWidths: List<Double> = emptyList(),
    val merges: List<String> = emptyList(),
    val rightToLeft: Boolean = false,
    val hidden: Boolean = false,
)

/**
 * كاتب xlsx مصغّر (بدون تبعيات) — يدعم: عدة شيتات، أنماط، RTL، دمج خلايا، عرض أعمدة، إخفاء شيت.
 * الفحص المرجعي يتم بنفس validator المشروع (tools/validate_package.py).
 */
object XlsxWriter {

    fun write(sheets: List<XlsxSheet>): ByteArray {
        val baos = ByteArrayOutputStream()
        ZipOutputStream(baos).use { zos ->
            put(zos, "[Content_Types].xml", contentTypes(sheets.size))
            put(zos, "_rels/.rels", rootRels)
            put(zos, "xl/workbook.xml", workbook(sheets))
            put(zos, "xl/_rels/workbook.xml.rels", workbookRels(sheets.size))
            put(zos, "xl/styles.xml", stylesXml)
            sheets.forEachIndexed { i, sheet ->
                put(zos, "xl/worksheets/sheet${i + 1}.xml", sheetXml(sheet))
            }
        }
        return baos.toByteArray()
    }

    /** شيت آلي بسيط (بدون أنماط) — للشيتات التي يقرأها الويب. */
    fun plain(name: String, rows: List<List<Any?>>, hidden: Boolean = false): XlsxSheet =
        XlsxSheet(
            name = name,
            rows = rows.map { row -> XlsxRow(row.map { XlsxCell(it) }) },
            hidden = hidden,
        )

    private fun put(zos: ZipOutputStream, name: String, content: String) {
        zos.putNextEntry(ZipEntry(name))
        zos.write(content.toByteArray(Charsets.UTF_8))
        zos.closeEntry()
    }

    private val rootRels: String =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">" +
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>" +
            "</Relationships>"

    private fun contentTypes(sheetCount: Int): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">")
        sb.append("<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>")
        sb.append("<Default Extension=\"xml\" ContentType=\"application/xml\"/>")
        sb.append("<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>")
        for (i in 1..sheetCount) {
            sb.append("<Override PartName=\"/xl/worksheets/sheet$i.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>")
        }
        sb.append("<Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>")
        sb.append("</Types>")
        return sb.toString()
    }

    private fun workbook(sheets: List<XlsxSheet>): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" ")
        sb.append("xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>")
        sheets.forEachIndexed { i, sheet ->
            sb.append("<sheet name=\"${escapeAttr(sheet.name)}\" sheetId=\"${i + 1}\"")
            if (sheet.hidden) sb.append(" state=\"hidden\"")
            sb.append(" r:id=\"rId${i + 1}\"/>")
        }
        sb.append("</sheets></workbook>")
        return sb.toString()
    }

    private fun workbookRels(sheetCount: Int): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">")
        for (i in 1..sheetCount) {
            sb.append("<Relationship Id=\"rId$i\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet$i.xml\"/>")
        }
        sb.append("<Relationship Id=\"rId${sheetCount + 1}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>")
        sb.append("</Relationships>")
        return sb.toString()
    }

    private fun sheetXml(sheet: XlsxSheet): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">")
        sb.append("<sheetViews><sheetView ")
        if (sheet.rightToLeft) sb.append("rightToLeft=\"1\" ")
        sb.append("workbookViewId=\"0\"/></sheetViews>")
        if (sheet.colWidths.isNotEmpty()) {
            sb.append("<cols>")
            sheet.colWidths.forEachIndexed { i, width ->
                sb.append("<col min=\"${i + 1}\" max=\"${i + 1}\" width=\"$width\" customWidth=\"1\"/>")
            }
            sb.append("</cols>")
        }
        sb.append("<sheetData>")
        sheet.rows.forEachIndexed { rIdx, row ->
            val r = rIdx + 1
            sb.append("<row r=\"$r\"")
            row.height?.let { sb.append(" ht=\"$it\" customHeight=\"1\"") }
            sb.append(">")
            row.cells.forEachIndexed { cIdx, cell ->
                sb.append(cellXml(colLetter(cIdx) + r, cell))
            }
            sb.append("</row>")
        }
        sb.append("</sheetData>")
        if (sheet.merges.isNotEmpty()) {
            sb.append("<mergeCells count=\"${sheet.merges.size}\">")
            sheet.merges.forEach { sb.append("<mergeCell ref=\"$it\"/>") }
            sb.append("</mergeCells>")
        }
        sb.append("</worksheet>")
        return sb.toString()
    }

    private fun cellXml(ref: String, cell: XlsxCell): String {
        val styleAttr = if (cell.style != XlsxStyle.DEFAULT) " s=\"${cell.style}\"" else ""
        val value = cell.value
        if (value == null || value == "") {
            // خلية بأنماط فقط (تعبئة/حدود ضمن نطاق مدمج)
            return if (cell.style != XlsxStyle.DEFAULT) "<c r=\"$ref\"$styleAttr/>" else ""
        }
        return when (value) {
            is Boolean -> "<c r=\"$ref\"$styleAttr><v>${if (value) 1 else 0}</v></c>"
            is Int -> "<c r=\"$ref\"$styleAttr><v>$value</v></c>"
            is Long -> "<c r=\"$ref\"$styleAttr><v>$value</v></c>"
            is Double -> "<c r=\"$ref\"$styleAttr><v>$value</v></c>"
            is Float -> "<c r=\"$ref\"$styleAttr><v>$value</v></c>"
            else -> "<c r=\"$ref\"$styleAttr t=\"inlineStr\"><is><t xml:space=\"preserve\">${escapeText(value.toString())}</t></is></c>"
        }
    }

    private fun colLetter(idx: Int): String {
        var i = idx + 1
        val sb = StringBuilder()
        while (i > 0) {
            val rem = (i - 1) % 26
            sb.insert(0, 'A' + rem)
            i = (i - 1) / 26
        }
        return sb.toString()
    }

    private fun escapeText(text: String): String =
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    private fun escapeAttr(text: String): String =
        escapeText(text).replace("\"", "&quot;")

    // ===================== styles.xml =====================

    private class XfDef(val fontId: Int, val fillId: Int, val borderId: Int, val align: String?)

    private val XFS = listOf(
        XfDef(0, 0, 0, null),          // 0 DEFAULT
        XfDef(1, 2, 0, "center"),      // 1 TITLE
        XfDef(2, 3, 0, "right"),       // 2 SECTION
        XfDef(3, 8, 1, "right"),       // 3 LABEL
        XfDef(4, 0, 0, "rightWrap"),   // 4 VALUE
        XfDef(2, 3, 1, "centerWrap"),  // 5 HEADER
        XfDef(4, 0, 1, "rightWrap"),   // 6 CELL
        XfDef(4, 0, 1, "centerWrap"),  // 7 CELL_CENTER
        XfDef(5, 5, 1, "center"),      // 8 OK
        XfDef(6, 6, 1, "center"),      // 9 MINOR
        XfDef(7, 7, 1, "center"),      // 10 FAULT
        XfDef(8, 0, 0, "rightWrap"),   // 11 FOOTER
        XfDef(9, 0, 0, "right"),       // 12 BOLD_VALUE
        XfDef(4, 0, 1, "center"),      // 13 CELL_NUM
    )

    private val stylesXml: String = buildStyles()

    private fun buildStyles(): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">")

        sb.append("<fonts count=\"10\">")
        sb.append("<font><sz val=\"11\"/><color theme=\"1\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"16\"/><color rgb=\"FFFFFFFF\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"11\"/><color rgb=\"FFFFFFFF\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"11\"/><color rgb=\"FF333333\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><sz val=\"11\"/><color rgb=\"FF333333\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"11\"/><color rgb=\"FF006100\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"11\"/><color rgb=\"FF9C6500\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"11\"/><color rgb=\"FF9C0006\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><sz val=\"9\"/><color rgb=\"FF808080\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("<font><b/><sz val=\"11\"/><color rgb=\"FF1F4E79\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        sb.append("</fonts>")

        sb.append("<fills count=\"9\">")
        sb.append("<fill><patternFill patternType=\"none\"/></fill>")
        sb.append("<fill><patternFill patternType=\"gray125\"/></fill>")
        sb.append(solidFill("FF1F4E79"))
        sb.append(solidFill("FF2E75B6"))
        sb.append(solidFill("FFD9E2F3"))
        sb.append(solidFill("FFC6EFCE"))
        sb.append(solidFill("FFFFEB9C"))
        sb.append(solidFill("FFFFC7CE"))
        sb.append(solidFill("FFF2F2F2"))
        sb.append("</fills>")

        sb.append("<borders count=\"2\">")
        sb.append("<border><left/><right/><top/><bottom/><diagonal/></border>")
        sb.append(
            "<border>" +
                "<left style=\"thin\"><color rgb=\"FFB0B0B0\"/></left>" +
                "<right style=\"thin\"><color rgb=\"FFB0B0B0\"/></right>" +
                "<top style=\"thin\"><color rgb=\"FFB0B0B0\"/></top>" +
                "<bottom style=\"thin\"><color rgb=\"FFB0B0B0\"/></bottom>" +
                "<diagonal/></border>",
        )
        sb.append("</borders>")

        sb.append("<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>")
        sb.append("<cellXfs count=\"${XFS.size}\">")
        XFS.forEach { sb.append(xfXml(it)) }
        sb.append("</cellXfs>")

        sb.append("</styleSheet>")
        return sb.toString()
    }

    private fun solidFill(argb: String): String =
        "<fill><patternFill patternType=\"solid\"><fgColor rgb=\"$argb\"/><bgColor indexed=\"64\"/></patternFill></fill>"

    private fun xfXml(xf: XfDef): String {
        val sb = StringBuilder(
            "<xf numFmtId=\"0\" fontId=\"${xf.fontId}\" fillId=\"${xf.fillId}\" borderId=\"${xf.borderId}\" xfId=\"0\"",
        )
        if (xf.fontId != 0) sb.append(" applyFont=\"1\"")
        if (xf.fillId != 0) sb.append(" applyFill=\"1\"")
        if (xf.borderId != 0) sb.append(" applyBorder=\"1\"")
        val align = alignmentXml(xf.align)
        if (align.isNotEmpty()) {
            sb.append(" applyAlignment=\"1\">").append(align).append("</xf>")
        } else {
            sb.append("/>")
        }
        return sb.toString()
    }

    private fun alignmentXml(kind: String?): String = when (kind) {
        "center" -> "<alignment horizontal=\"center\" vertical=\"center\" readingOrder=\"2\"/>"
        "right" -> "<alignment horizontal=\"right\" vertical=\"center\" readingOrder=\"2\"/>"
        "rightWrap" -> "<alignment horizontal=\"right\" vertical=\"center\" wrapText=\"1\" readingOrder=\"2\"/>"
        "centerWrap" -> "<alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\" readingOrder=\"2\"/>"
        else -> ""
    }
}
