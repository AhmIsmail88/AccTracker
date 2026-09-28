package com.protrack.app.domain

data class ChecklistItem(
    val code: String,
    val nameAr: String,
    val scope: String,
)

/**
 * بنود العنبر الـ12 — مطابقة لـ contract/checklist_items.json (قائمة مؤقتة).
 */
object ChecklistCatalog {
    val items: List<ChecklistItem> = listOf(
        ChecklistItem("CHK-01", "تسريب أو رطوبة حول المضخة", "PUMP"),
        ChecklistItem("CHK-02", "اهتزاز غير طبيعي", "PUMP"),
        ChecklistItem("CHK-03", "صوت غير طبيعي", "PUMP"),
        ChecklistItem("CHK-04", "مستوى الزيت / التشحيم", "PUMP"),
        ChecklistItem("CHK-05", "حالة السيل الميكانيكي", "PUMP"),
        ChecklistItem("CHK-06", "قراءة ضغط السحب والطرد", "PUMP"),
        ChecklistItem("CHK-07", "درجة حرارة المحرك والمضخة", "PUMP"),
        ChecklistItem("CHK-08", "عمل العوامة أو حساس المستوى", "STATION"),
        ChecklistItem("CHK-09", "نظافة غرفة المضخات والتهوية", "STATION"),
        ChecklistItem("CHK-10", "حالة المحابس والمواسير", "STATION"),
        ChecklistItem("CHK-11", "سلامة اللوحة الكهربائية والتأريض", "STATION"),
        ChecklistItem("CHK-12", "قراءة عدّاد ساعات التشغيل", "STATION"),
    )

    fun nameFor(code: String): String = items.firstOrNull { it.code == code }?.nameAr ?: code
}
