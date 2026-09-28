package com.protrack.app.domain.export

import java.io.ByteArrayOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * كاتب xlsx مصغّر بنفس بنية أدوات العقد (Phase 0) — الفحص المرجعي يتم
 * بنفس validator المشروع.
 */
object XlsxWriter {

    fun write(sheets: LinkedHashMap<String, List<List<Any?>>>): ByteArray {
        val names = sheets.keys.toList()
        val baos = ByteArrayOutputStream()
        ZipOutputStream(baos).use { zos ->
            put(zos, "[Content_Types].xml", contentTypes(names))
            put(zos, "_rels/.rels", rootRels)
            put(zos, "xl/workbook.xml", workbook(names))
            put(zos, "xl/_rels/workbook.xml.rels", workbookRels(names.size))
            var i = 0
            for ((_, rows) in sheets) {
                put(zos, "xl/worksheets/sheet${i + 1}.xml", sheetXml(rows))
                i += 1
            }
        }
        return baos.toByteArray()
    }

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

    private fun contentTypes(sheetNames: List<String>): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">")
        sb.append("<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>")
        sb.append("<Default Extension=\"xml\" ContentType=\"application/xml\"/>")
        sb.append("<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>")
        sheetNames.forEachIndexed { i, _ ->
            sb.append("<Override PartName=\"/xl/worksheets/sheet${i + 1}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>")
        }
        sb.append("</Types>")
        return sb.toString()
    }

    private fun workbook(names: List<String>): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" ")
        sb.append("xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>")
        names.forEachIndexed { i, name ->
            sb.append("<sheet name=\"${escapeAttr(name)}\" sheetId=\"${i + 1}\" r:id=\"rId${i + 1}\"/>")
        }
        sb.append("</sheets></workbook>")
        return sb.toString()
    }

    private fun workbookRels(count: Int): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">")
        for (i in 1..count) {
            sb.append("<Relationship Id=\"rId$i\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet$i.xml\"/>")
        }
        sb.append("</Relationships>")
        return sb.toString()
    }

    private fun sheetXml(rows: List<List<Any?>>): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>")
        rows.forEachIndexed { rIdx, row ->
            val r = rIdx + 1
            sb.append("<row r=\"$r\">")
            for ((cIdx, value) in row.withIndex()) {
                if (value == null || value == "") continue
                val ref = colLetter(cIdx) + r
                when (value) {
                    is Boolean -> sb.append("<c r=\"$ref\"><v>${if (value) 1 else 0}</v></c>")
                    is Int -> sb.append("<c r=\"$ref\"><v>$value</v></c>")
                    is Long -> sb.append("<c r=\"$ref\"><v>$value</v></c>")
                    is Double -> sb.append("<c r=\"$ref\"><v>$value</v></c>")
                    is Float -> sb.append("<c r=\"$ref\"><v>$value</v></c>")
                    else -> sb.append(
                        "<c r=\"$ref\" t=\"inlineStr\"><is><t xml:space=\"preserve\">${escapeText(value.toString())}</t></is></c>",
                    )
                }
            }
            sb.append("</row>")
        }
        sb.append("</sheetData></worksheet>")
        return sb.toString()
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
}
