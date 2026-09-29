package com.protrack.app.ui.visit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.protrack.app.data.ExportOutcome
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.data.PackageExporter
import com.protrack.app.data.PhotoManager
import com.protrack.app.data.VisitRepository
import com.protrack.app.data.db.VisitChecklistEntity
import com.protrack.app.data.db.VisitEntity
import com.protrack.app.data.db.VisitEquipmentEntity
import com.protrack.app.data.db.VisitPhotoEntity
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.TreeBuilder
import com.protrack.app.domain.TreeNode
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.io.File

data class LocationOption(val code: String, val name: String, val path: String)

class VisitViewModel(
    private val hierarchyRepository: HierarchyRepository,
    private val visitRepository: VisitRepository,
    private val photoManager: PhotoManager,
    private val exporter: PackageExporter,
) : ViewModel() {

    enum class Step { LOCATION, EQUIPMENT, CHECKLIST, REVIEW }

    private val _step = MutableStateFlow(Step.LOCATION)
    private val _visitId = MutableStateFlow<Long?>(null)
    private val _exportOutcome = MutableStateFlow<ExportOutcome?>(null)
    private val _busy = MutableStateFlow(false)

    val step: StateFlow<Step> = _step
    val exportOutcome: StateFlow<ExportOutcome?> = _exportOutcome
    val busy: StateFlow<Boolean> = _busy

    val hierarchyTree: StateFlow<List<TreeNode>> =
        hierarchyRepository.data
            .map { data ->
                TreeBuilder.build(data.projects, data.regions, data.zones, data.locations)
            }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val locationOptions: StateFlow<List<LocationOption>> =
        hierarchyTree
            .map { tree -> collectLocations(tree) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    @OptIn(ExperimentalCoroutinesApi::class)
    val visit: StateFlow<VisitEntity?> = _visitId
        .flatMapLatest { id -> if (id == null) flowOf(null) else visitRepository.visit(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    @OptIn(ExperimentalCoroutinesApi::class)
    val equipment: StateFlow<List<VisitEquipmentEntity>> = _visitId
        .flatMapLatest { id -> if (id == null) flowOf(emptyList()) else visitRepository.equipment(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    @OptIn(ExperimentalCoroutinesApi::class)
    val checklist: StateFlow<List<VisitChecklistEntity>> = _visitId
        .flatMapLatest { id -> if (id == null) flowOf(emptyList()) else visitRepository.checklist(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    @OptIn(ExperimentalCoroutinesApi::class)
    val photos: StateFlow<List<VisitPhotoEntity>> = _visitId
        .flatMapLatest { id -> if (id == null) flowOf(emptyList()) else visitRepository.photos(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun chooseLocation(code: String) {
        if (_visitId.value != null) {
            // الزيارة اتعملت بالفعل — «متابعة» ترجع للخطوة التالية
            _step.value = Step.EQUIPMENT
            return
        }
        viewModelScope.launch {
            _visitId.value = visitRepository.createVisit(code)
            _step.value = Step.EQUIPMENT
        }
    }

    /** إيجاد عقدة في الشجرة الكاملة (للانتقال التلقائي لإضافة موقع تحت عنصر). */
    suspend fun findNode(code: String): TreeNode? {
        val data = hierarchyRepository.data.first()
        val tree = TreeBuilder.build(data.projects, data.regions, data.zones, data.locations)
        fun rec(nodes: List<TreeNode>): TreeNode? {
            for (node in nodes) {
                if (node.code == code) return node
                rec(node.children)?.let { return it }
            }
            return null
        }
        return rec(tree)
    }

    fun addEquipment(kind: String, model: String, quantity: Int) {
        val id = _visitId.value ?: return
        viewModelScope.launch { visitRepository.addEquipment(id, kind, model, quantity) }
    }

    fun updateEquipment(entity: VisitEquipmentEntity) {
        viewModelScope.launch { visitRepository.updateEquipment(entity) }
    }

    fun deleteEquipment(entity: VisitEquipmentEntity) {
        viewModelScope.launch { visitRepository.deleteEquipment(entity) }
    }

    fun setChecklistStatus(item: VisitChecklistEntity, status: String) {
        viewModelScope.launch { visitRepository.updateChecklist(item.copy(status = status)) }
    }

    fun saveChecklistItem(item: VisitChecklistEntity, name: String, status: String, note: String) {
        viewModelScope.launch {
            visitRepository.updateChecklist(item.copy(itemName = name.trim(), status = status, note = note.trim()))
        }
    }

    fun addChecklistItem(name: String, status: String, note: String) {
        val id = _visitId.value ?: return
        viewModelScope.launch { visitRepository.addChecklistItem(id, name, status, note) }
    }

    fun deleteChecklistItem(item: VisitChecklistEntity) {
        viewModelScope.launch { visitRepository.deleteChecklistItem(item) }
    }

    /** استئناف زيارة سابقة (مسودة) — يكمل من خطوة المعدات. */
    fun resume(visitId: Long) {
        if (_visitId.value == visitId) return
        _visitId.value = visitId
        _step.value = Step.EQUIPMENT
        _exportOutcome.value = null
    }

    fun newPhotoFile(): File? {
        val id = _visitId.value ?: return null
        return photoManager.newPhotoFile(id)
    }

    /** يلتقط صورة ويسجلها مع اسم الموقع (للختم على الصورة). */
    fun attachPhoto(targetType: String, targetRef: String, file: File) {
        val id = _visitId.value ?: return
        viewModelScope.launch {
            val visit = visitRepository.visitById(id)
            val siteName = visit?.locationCode?.let { code -> findNodeByCode(code)?.name }
            photoManager.attachPhoto(id, targetType, targetRef, file, siteName)
        }
    }

    private suspend fun findNodeByCode(code: String): TreeNode? {
        val data = hierarchyRepository.data.first()
        val tree = TreeBuilder.build(data.projects, data.regions, data.zones, data.locations)
        fun rec(nodes: List<TreeNode>): TreeNode? {
            for (node in nodes) {
                if (node.code == code) return node
                rec(node.children)?.let { return it }
            }
            return null
        }
        return rec(tree)
    }

    fun next() {
        _step.value = when (_step.value) {
            Step.LOCATION -> Step.EQUIPMENT
            Step.EQUIPMENT -> Step.CHECKLIST
            Step.CHECKLIST -> Step.REVIEW
            Step.REVIEW -> Step.REVIEW
        }
    }

    fun back() {
        _step.value = when (_step.value) {
            Step.LOCATION -> Step.LOCATION
            Step.EQUIPMENT -> Step.LOCATION
            Step.CHECKLIST -> Step.EQUIPMENT
            Step.REVIEW -> Step.CHECKLIST
        }
    }

    fun export(notes: String) {
        val id = _visitId.value ?: return
        if (_busy.value) return
        viewModelScope.launch {
            _busy.value = true
            _exportOutcome.value = exporter.export(id, notes)
            _busy.value = false
        }
    }

    fun reset() {
        _visitId.value = null
        _step.value = Step.LOCATION
        _exportOutcome.value = null
        _busy.value = false
    }

    private fun collectLocations(tree: List<TreeNode>): List<LocationOption> {
        val out = mutableListOf<LocationOption>()
        fun rec(nodes: List<TreeNode>, path: List<String>) {
            for (node in nodes) {
                val newPath = path + node.name
                if (node.type == NodeType.LOCATION) {
                    out += LocationOption(node.code, node.name, newPath.dropLast(1).joinToString(" / "))
                }
                rec(node.children, newPath)
            }
        }
        rec(tree, emptyList())
        return out
    }

    class Factory(
        private val hierarchyRepository: HierarchyRepository,
        private val visitRepository: VisitRepository,
        private val photoManager: PhotoManager,
        private val exporter: PackageExporter,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            VisitViewModel(hierarchyRepository, visitRepository, photoManager, exporter) as T
    }
}
