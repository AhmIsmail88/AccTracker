package com.protrack.app.ui.visit

import android.Manifest
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import com.protrack.app.R
import com.protrack.app.data.ExportOutcome
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.data.PackageExporter
import com.protrack.app.data.PhotoManager
import com.protrack.app.data.VisitRepository
import com.protrack.app.data.db.VisitChecklistEntity
import com.protrack.app.data.db.VisitEquipmentEntity
import com.protrack.app.data.db.VisitEntity
import com.protrack.app.data.db.VisitPhotoEntity
import com.protrack.app.domain.ChecklistCatalog
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.TreeBuilder
import com.protrack.app.domain.TreeNode
import com.protrack.app.ui.capture.CameraCaptureScreen
import kotlinx.coroutines.flow.first
import java.io.File

private const val KIND_MAIN_PUMP = "MAIN_PUMP"
private const val KIND_SUBMERSIBLE = "SUBMERSIBLE_PUMP"
private const val KIND_FILTER = "FILTER"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VisitScreen(
    hierarchyRepository: HierarchyRepository,
    visitRepository: VisitRepository,
    photoManager: PhotoManager,
    exporter: PackageExporter,
    onBack: () -> Unit,
    resumeVisitId: Long? = null,
    onAddLocation: (String?) -> Unit = {},
) {
    val viewModel: VisitViewModel = viewModel(
        factory = VisitViewModel.Factory(hierarchyRepository, visitRepository, photoManager, exporter),
    )
    val step by viewModel.step.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val outcome by viewModel.exportOutcome.collectAsState()
    val photos by viewModel.photos.collectAsState()
    var notes by rememberSaveable { mutableStateOf("") }
    var showPhotos by remember { mutableStateOf(false) }
    var pendingLocationCode by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(resumeVisitId) {
        if (resumeVisitId != null) {
            viewModel.resume(resumeVisitId)
        }
    }

    val context = LocalContext.current
    var cameraTarget by remember { mutableStateOf<CameraTarget?>(null) }
    var pendingCameraTarget by remember { mutableStateOf<CameraTarget?>(null) }
    var showPermissionMessage by remember { mutableStateOf(false) }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        if (result[Manifest.permission.CAMERA] == true) {
            cameraTarget = pendingCameraTarget
        } else {
            showPermissionMessage = true
        }
        pendingCameraTarget = null
    }

    val startCapture: (String, String) -> Unit = { type, ref ->
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
        if (granted) {
            cameraTarget = CameraTarget(type, ref)
        } else {
            pendingCameraTarget = CameraTarget(type, ref)
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.CAMERA,
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                ),
            )
        }
    }

    val activeCamera = cameraTarget
    if (activeCamera != null) {
        CameraCaptureScreen(
            onCaptured = { file ->
                viewModel.attachPhoto(activeCamera.type, activeCamera.ref, file)
                cameraTarget = null
            },
            onCancel = { cameraTarget = null },
            fileFactory = { viewModel.newPhotoFile() ?: File(context.filesDir, "photo.jpg") },
        )
        return
    }

    if (showPhotos) {
        VisitPhotosScreen(photos = photos, onBack = { showPhotos = false })
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(stringResource(R.string.visit_title))
                        Text(
                            text = stringResource(R.string.visit_step_of, stepNumber(step), 4),
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = stringResource(R.string.nav_back),
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { showPhotos = true }) {
                        Icon(
                            imageVector = Icons.Default.PhotoLibrary,
                            contentDescription = stringResource(R.string.photos_title),
                        )
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            ) {
                when (step) {
                    VisitViewModel.Step.LOCATION -> LocationStep(
                        viewModel = viewModel,
                        onAddLocation = onAddLocation,
                        onLocationPicked = { pendingLocationCode = it },
                    )
                    VisitViewModel.Step.EQUIPMENT -> EquipmentStep(
                        viewModel = viewModel,
                        photos = photos,
                        onAddPhoto = startCapture,
                    )
                    VisitViewModel.Step.CHECKLIST -> ChecklistStep(
                        viewModel = viewModel,
                        photos = photos,
                        onAddPhoto = startCapture,
                    )
                    VisitViewModel.Step.REVIEW -> ReviewStep(
                        viewModel = viewModel,
                        notes = notes,
                        onNotesChange = { notes = it },
                        busy = busy,
                        outcome = outcome,
                        photosCount = photos.size,
                        onShowPhotos = { showPhotos = true },
                    )
                }
            }
            StepNavBar(
                viewModel = viewModel,
                step = step,
                busy = busy,
                outcome = outcome,
                notes = notes,
                pendingLocationCode = pendingLocationCode,
            )
        }
    }

    if (showPermissionMessage) {
        AlertDialog(
            onDismissRequest = { showPermissionMessage = false },
            title = { Text(stringResource(R.string.camera_permission_denied)) },
            confirmButton = {
                TextButton(onClick = { showPermissionMessage = false }) {
                    Text(stringResource(R.string.done))
                }
            },
        )
    }
}

private fun stepNumber(step: VisitViewModel.Step): Int = when (step) {
    VisitViewModel.Step.LOCATION -> 1
    VisitViewModel.Step.EQUIPMENT -> 2
    VisitViewModel.Step.CHECKLIST -> 3
    VisitViewModel.Step.REVIEW -> 4
}

@Composable
private fun StepNavBar(
    viewModel: VisitViewModel,
    step: VisitViewModel.Step,
    busy: Boolean,
    outcome: ExportOutcome?,
    notes: String,
    pendingLocationCode: String?,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (step == VisitViewModel.Step.LOCATION && outcome == null) {
            Button(
                onClick = { pendingLocationCode?.let { viewModel.chooseLocation(it) } },
                enabled = pendingLocationCode != null && !busy,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.visit_next))
            }
        }
        if (step != VisitViewModel.Step.LOCATION && outcome == null) {
            OutlinedButton(
                onClick = { viewModel.back() },
                enabled = !busy,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.visit_previous))
            }
        }
        if (step == VisitViewModel.Step.EQUIPMENT || step == VisitViewModel.Step.CHECKLIST) {
            Button(
                onClick = { viewModel.next() },
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.visit_next))
            }
        } else if (step == VisitViewModel.Step.REVIEW && outcome == null) {
            Button(
                onClick = { viewModel.export(notes) },
                enabled = !busy,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.visit_export))
            }
        }
    }
}

@Composable
private fun LocationStep(
    viewModel: VisitViewModel,
    onAddLocation: (String?) -> Unit,
    onLocationPicked: (String) -> Unit,
) {
    val tree by viewModel.hierarchyTree.collectAsState()
    var showPicker by remember { mutableStateOf(false) }
    var projectCode by remember { mutableStateOf<String?>(null) }
    var regionCode by remember { mutableStateOf<String?>(null) }
    var zoneCode by remember { mutableStateOf<String?>(null) }
    var chosen by remember { mutableStateOf<TreeNode?>(null) }

    val project = tree.firstOrNull { it.code == projectCode }
    val region = project?.children?.firstOrNull { it.code == regionCode }
    val zone = region?.children?.firstOrNull { it.code == zoneCode }

    val items: List<TreeNode> = when {
        zone != null -> zone.children
        region != null -> region.children
        project != null -> project.children
        else -> tree
    }
    val levelTitle = when {
        zone != null -> stringResource(R.string.visit_level_locations)
        region != null -> stringResource(R.string.visit_level_zones)
        project != null -> stringResource(R.string.visit_level_regions)
        else -> stringResource(R.string.visit_level_projects)
    }
    val pickerPath = listOfNotNull(project?.name, region?.name, zone?.name).joinToString(" ‹ ")
    val chosenPath = buildChosenPath(tree, chosen)
    val displayPath = if (chosen != null) chosenPath else stringResource(R.string.visit_pick_location)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text(
            text = stringResource(R.string.visit_select_location),
            style = MaterialTheme.typography.titleMedium,
        )
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedButton(
            onClick = { showPicker = true },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = displayPath.ifBlank { stringResource(R.string.visit_pick_location) },
                modifier = Modifier.weight(1f),
                maxLines = 1,
            )
            Icon(imageVector = Icons.Default.ArrowDropDown, contentDescription = null)
        }
        if (tree.isEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.visit_no_locations),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedButton(
            onClick = { onAddLocation(chosen?.code ?: zone?.code ?: region?.code ?: project?.code) },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(imageVector = Icons.Default.Add, contentDescription = null)
            Spacer(modifier = Modifier.width(4.dp))
            Text(stringResource(R.string.visit_add_location))
        }
    }

    if (showPicker) {
        AlertDialog(
            onDismissRequest = { showPicker = false },
            title = {
                Column {
                    Text(levelTitle)
                    if (pickerPath.isNotBlank()) {
                        Text(
                            text = pickerPath,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    if (zone != null) {
                        TextButton(onClick = { zoneCode = null }) {
                            Text(stringResource(R.string.visit_back_level))
                        }
                    } else if (region != null) {
                        TextButton(onClick = { regionCode = null }) {
                            Text(stringResource(R.string.visit_back_level))
                        }
                    } else if (project != null) {
                        TextButton(onClick = { projectCode = null }) {
                            Text(stringResource(R.string.visit_back_level))
                        }
                    }
                    if (items.isEmpty()) {
                        Text(
                            text = stringResource(R.string.visit_level_empty),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(vertical = 8.dp),
                        )
                        TextButton(
                            onClick = {
                                showPicker = false
                                onAddLocation(chosen?.code ?: zone?.code ?: region?.code ?: project?.code)
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(imageVector = Icons.Default.Add, contentDescription = null)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(stringResource(R.string.visit_add_location))
                        }
                    }
                    items.forEach { node ->
                        TextButton(
                            onClick = {
                                when {
                                    node.children.isEmpty() -> {
                                        // عنصر بدون أبناء (مشروع/منطقة/زون/موقع مفرد) — يُختار مباشرة كهدف الزيارة
                                        chosen = node
                                        onLocationPicked(node.code)
                                        showPicker = false
                                    }
                                    node.type == NodeType.PROJECT -> projectCode = node.code
                                    node.type == NodeType.REGION -> regionCode = node.code
                                    node.type == NodeType.ZONE -> zoneCode = node.code
                                    else -> Unit
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text(
                                text = node.name + if (node.status != "ACTIVE") {
                                    " (" + stringResource(R.string.status_inactive) + ")"
                                } else {
                                    ""
                                },
                                modifier = Modifier.weight(1f),
                                textAlign = TextAlign.Right,
                            )
                        }
                    }
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { showPicker = false }) {
                    Text(stringResource(R.string.close))
                }
            },
        )
    }
}

/** مسار العقدة المختارة كاملًا (مشروع ‹ منطقة ‹ زون ‹ موقع). */
private fun buildChosenPath(tree: List<TreeNode>, chosen: TreeNode?): String {
    if (chosen == null) return ""
    val acc = mutableListOf<String>()
    fun rec(nodes: List<TreeNode>, path: List<String>): Boolean {
        for (node in nodes) {
            val newPath = path + node.name
            if (node.code == chosen.code) {
                acc.addAll(newPath)
                return true
            }
            if (rec(node.children, newPath)) return true
        }
        return false
    }
    rec(tree, emptyList())
    return acc.joinToString(" ‹ ")
}

private fun findTreeNode(nodes: List<TreeNode>, code: String): TreeNode? {
    for (node in nodes) {
        if (node.code == code) return node
        findTreeNode(node.children, code)?.let { return it }
    }
    return null
}

@Composable
private fun EquipmentStep(
    viewModel: VisitViewModel,
    photos: List<VisitPhotoEntity>,
    onAddPhoto: (String, String) -> Unit,
) {
    val equipment by viewModel.equipment.collectAsState()
    var showAdd by remember { mutableStateOf(false) }
    var editTarget by remember { mutableStateOf<VisitEquipmentEntity?>(null) }
    var deleteTarget by remember { mutableStateOf<VisitEquipmentEntity?>(null) }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.visit_equipment_title),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            Button(onClick = { showAdd = true }) {
                Icon(imageVector = Icons.Default.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text(stringResource(R.string.visit_add_equipment))
            }
        }
        if (equipment.isEmpty()) {
            Text(
                text = stringResource(R.string.visit_no_equipment),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(16.dp),
            )
        } else {
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(equipment, key = { it.id }) { item ->
                    val photoCount = photos.count { it.targetRef == "${item.kind}-${item.tag}" }
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 4.dp)
                            .clickable { editTarget = item },
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(
                                text = "${item.tag} — ${item.model}",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Text(
                                text = "${item.kind} • ${item.runningHours ?: "-"} h • " +
                                    "${item.pressureBar ?: "-"} bar • ${statusLabel(item.status)}" +
                                    if (photoCount > 0) " • 📷 $photoCount" else "",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }
    }

    if (showAdd) {
        AddEquipmentDialog(
            onDismiss = { showAdd = false },
            onConfirm = { kind, model, quantity ->
                viewModel.addEquipment(kind, model, quantity)
                showAdd = false
            },
        )
    }

    editTarget?.let { entity ->
        EquipmentEditDialog(
            entity = entity,
            photos = photos.filter { it.targetRef == "${entity.kind}-${entity.tag}" },
            onAddPhoto = {
                onAddPhoto("EQUIPMENT", "${entity.kind}-${entity.tag}")
                editTarget = null
            },
            onDelete = {
                deleteTarget = entity
                editTarget = null
            },
            onDismiss = { editTarget = null },
            onSave = { updated ->
                viewModel.updateEquipment(updated)
                editTarget = null
            },
        )
    }

    deleteTarget?.let { entity ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text(stringResource(R.string.equipment_delete_title)) },
            text = { Text(stringResource(R.string.equipment_delete_confirm, "${entity.tag} — ${entity.model}")) },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.deleteEquipment(entity)
                        deleteTarget = null
                    },
                ) {
                    Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteTarget = null }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }
}

@Composable
private fun ChecklistStep(
    viewModel: VisitViewModel,
    photos: List<VisitPhotoEntity>,
    onAddPhoto: (String, String) -> Unit,
) {
    val checklist by viewModel.checklist.collectAsState()
    var showAddDialog by remember { mutableStateOf(false) }
    var editTarget by remember { mutableStateOf<VisitChecklistEntity?>(null) }
    var deleteTarget by remember { mutableStateOf<VisitChecklistEntity?>(null) }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.visit_checklist_title),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            Button(onClick = { showAddDialog = true }) {
                Icon(imageVector = Icons.Default.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text(stringResource(R.string.checklist_add_item))
            }
        }
        LazyColumn(modifier = Modifier.weight(1f)) {
            items(checklist, key = { it.id }) { item ->
                ChecklistItemCard(
                    item = item,
                    name = checklistDisplayName(item),
                    photoCount = photos.count { it.targetType == "CHECKLIST" && it.targetRef == item.itemCode },
                    onStatus = { status -> viewModel.setChecklistStatus(item, status) },
                    onAddPhoto = { onAddPhoto("CHECKLIST", item.itemCode) },
                    onEdit = { editTarget = item },
                )
            }
        }
    }

    if (showAddDialog) {
        ChecklistItemDialog(
            title = stringResource(R.string.checklist_add_item),
            initialName = "",
            initialStatus = "OK",
            initialNote = "",
            requireName = true,
            onDismiss = { showAddDialog = false },
            onConfirm = { name, status, note ->
                if (name.isNotBlank()) viewModel.addChecklistItem(name, status, note)
                showAddDialog = false
            },
            onDelete = null,
        )
    }

    editTarget?.let { item ->
        ChecklistItemDialog(
            title = stringResource(R.string.checklist_edit_item),
            initialName = checklistDisplayName(item),
            initialStatus = item.status,
            initialNote = item.note,
            requireName = true,
            onDismiss = { editTarget = null },
            onConfirm = { name, status, note ->
                viewModel.saveChecklistItem(item, name, status, note)
                editTarget = null
            },
            onDelete = {
                deleteTarget = item
                editTarget = null
            },
        )
    }

    deleteTarget?.let { item ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text(stringResource(R.string.checklist_delete_item)) },
            text = { Text(stringResource(R.string.checklist_delete_confirm, checklistDisplayName(item))) },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.deleteChecklistItem(item)
                        deleteTarget = null
                    },
                ) {
                    Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteTarget = null }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }
}

private fun checklistDisplayName(item: VisitChecklistEntity): String =
    if (item.itemName.isNotBlank()) item.itemName else ChecklistCatalog.nameFor(item.itemCode)

@Composable
private fun ChecklistItemCard(
    item: VisitChecklistEntity,
    name: String,
    photoCount: Int,
    onStatus: (String) -> Unit,
    onAddPhoto: () -> Unit,
    onEdit: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(name, style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = (if (item.isCustom) stringResource(R.string.checklist_custom_badge) else item.itemCode) +
                            if (photoCount > 0) " • 📷 $photoCount" else "",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
                ChecklistStatusDropdown(status = item.status, onSelect = onStatus)
                IconButton(onClick = onAddPhoto) {
                    Icon(
                        imageVector = Icons.Default.PhotoCamera,
                        contentDescription = stringResource(R.string.checklist_photo_add),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
                IconButton(onClick = onEdit) {
                    Icon(
                        imageVector = Icons.Default.Edit,
                        contentDescription = stringResource(R.string.checklist_edit_item),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            if (item.note.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "📝 " + item.note,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun ChecklistStatusDropdown(status: String, onSelect: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        Button(
            onClick = { expanded = true },
            colors = ButtonDefaults.buttonColors(containerColor = checklistStatusColor(status)),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
        ) {
            Text(checklistStatusLabel(status))
            Icon(imageVector = Icons.Default.ArrowDropDown, contentDescription = null)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            listOf("OK", "MINOR", "FAULT").forEach { option ->
                DropdownMenuItem(
                    text = { Text(checklistStatusLabel(option)) },
                    onClick = {
                        expanded = false
                        onSelect(option)
                    },
                )
            }
        }
    }
}

@Composable
private fun checklistStatusLabel(status: String): String = when (status) {
    "OK" -> stringResource(R.string.chk_ok)
    "MINOR" -> stringResource(R.string.chk_minor)
    else -> stringResource(R.string.chk_fault)
}

private fun checklistStatusColor(status: String): Color = when (status) {
    "OK" -> Color(0xFF2E7D32)
    "MINOR" -> Color(0xFFB26A00)
    else -> Color(0xFFC62828)
}

@Composable
private fun ChecklistItemDialog(
    title: String,
    initialName: String,
    initialStatus: String,
    initialNote: String,
    requireName: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String, String, String) -> Unit,
    onDelete: (() -> Unit)?,
) {
    var name by remember { mutableStateOf(initialName) }
    var status by remember { mutableStateOf(initialStatus) }
    var note by remember { mutableStateOf(initialNote) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.checklist_item_name)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    text = stringResource(R.string.checklist_status_label),
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(top = 10.dp, bottom = 2.dp),
                )
                ChecklistStatusDropdown(status = status, onSelect = { status = it })
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it },
                    label = { Text(stringResource(R.string.checklist_note_label)) },
                    minLines = 2,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp),
                )
            }
        },
        confirmButton = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (onDelete != null) {
                    TextButton(onClick = onDelete) {
                        Text(
                            text = stringResource(R.string.checklist_delete_item),
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }
                TextButton(
                    onClick = { onConfirm(name, status, note) },
                    enabled = !requireName || name.isNotBlank(),
                ) {
                    Text(stringResource(R.string.save))
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.cancel))
            }
        },
    )
}

@Composable
private fun ReviewStep(
    viewModel: VisitViewModel,
    notes: String,
    onNotesChange: (String) -> Unit,
    busy: Boolean,
    outcome: ExportOutcome?,
    photosCount: Int,
    onShowPhotos: () -> Unit,
) {
    val equipment by viewModel.equipment.collectAsState()
    val checklist by viewModel.checklist.collectAsState()
    val visit by viewModel.visit.collectAsState()
    val issues = checklist.count { it.status != "OK" }
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text(
            text = stringResource(R.string.visit_review_title),
            style = MaterialTheme.typography.titleMedium,
        )
        Spacer(modifier = Modifier.height(8.dp))
        val tree by viewModel.hierarchyTree.collectAsState()
        visit?.let { activeVisit ->
            val node = findTreeNode(tree, activeVisit.locationCode)
            val displayName = if (node != null) buildChosenPath(tree, node) else activeVisit.locationCode
            Text(
                text = stringResource(R.string.visit_location_label, displayName),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = stringResource(R.string.visit_equipment_count, equipment.size),
            style = MaterialTheme.typography.bodyMedium,
        )
        Text(
            text = stringResource(R.string.visit_issues_count, issues),
            style = MaterialTheme.typography.bodyMedium,
        )
        Text(
            text = stringResource(R.string.visit_photos_count, photosCount),
            style = MaterialTheme.typography.bodyMedium,
        )
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedButton(
            onClick = onShowPhotos,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.photos_open))
        }
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = notes,
            onValueChange = onNotesChange,
            label = { Text(stringResource(R.string.visit_notes_label)) },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2,
        )
        if (busy) {
            Spacer(modifier = Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.visit_exporting))
            }
        }
        if (outcome != null) {
            Spacer(modifier = Modifier.height(16.dp))
            if (outcome.ok) {
                Text(
                    text = stringResource(R.string.visit_export_ok),
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.titleSmall,
                )
                Text(
                    text = outcome.fileName.orEmpty(),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = { outcome.file?.let { sharePackage(context, it) } },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.visit_share))
                }
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(
                    onClick = { viewModel.reset() },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.visit_new_visit))
                }
            } else {
                Text(
                    text = stringResource(R.string.visit_export_failed) + ": " + outcome.error.orEmpty(),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

@Composable
private fun AddEquipmentDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String, Int) -> Unit,
) {
    var kind by remember { mutableStateOf(KIND_MAIN_PUMP) }
    var model by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("1") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.visit_add_equipment)) },
        text = {
            Column {
                Text(
                    text = stringResource(R.string.visit_kind),
                    style = MaterialTheme.typography.labelMedium,
                )
                Row(
                    modifier = Modifier
                        .horizontalScroll(rememberScrollState())
                        .padding(vertical = 4.dp),
                ) {
                    KindButton(stringResource(R.string.kind_main_pump), kind == KIND_MAIN_PUMP) { kind = KIND_MAIN_PUMP }
                    KindButton(stringResource(R.string.kind_submersible), kind == KIND_SUBMERSIBLE) { kind = KIND_SUBMERSIBLE }
                    KindButton(stringResource(R.string.kind_filter), kind == KIND_FILTER) { kind = KIND_FILTER }
                }
                OutlinedTextField(
                    value = model,
                    onValueChange = { model = it },
                    label = { Text(stringResource(R.string.visit_model)) },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = quantity,
                    onValueChange = { newValue -> quantity = newValue.filter { it in '0'..'9' } },
                    label = { Text(stringResource(R.string.visit_quantity)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val qty = quantity.toIntOrNull() ?: 1
                    if (model.isNotBlank() && qty >= 1) {
                        onConfirm(kind, model.trim(), qty)
                    }
                },
                enabled = model.isNotBlank(),
            ) {
                Text(stringResource(R.string.save))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.cancel))
            }
        },
    )
}

@Composable
private fun EquipmentEditDialog(
    entity: VisitEquipmentEntity,
    photos: List<VisitPhotoEntity>,
    onAddPhoto: () -> Unit,
    onDelete: () -> Unit,
    onDismiss: () -> Unit,
    onSave: (VisitEquipmentEntity) -> Unit,
) {
    var hours by remember { mutableStateOf(entity.runningHours?.toString() ?: "") }
    var pressure by remember { mutableStateOf(entity.pressureBar?.toString() ?: "") }
    var status by remember { mutableStateOf(entity.status) }
    var note by remember { mutableStateOf(entity.note) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("${entity.tag} — ${entity.model}") },
        text = {
            Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                OutlinedTextField(
                    value = hours,
                    onValueChange = { hours = it },
                    label = { Text(stringResource(R.string.visit_running_hours)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                )
                OutlinedTextField(
                    value = pressure,
                    onValueChange = { pressure = it },
                    label = { Text(stringResource(R.string.visit_pressure)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                )
                Text(
                    text = stringResource(R.string.visit_status_label),
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(top = 8.dp),
                )
                Row(
                    modifier = Modifier
                        .horizontalScroll(rememberScrollState())
                        .padding(vertical = 4.dp),
                ) {
                    KindButton(stringResource(R.string.status_running), status == "RUNNING") { status = "RUNNING" }
                    KindButton(stringResource(R.string.status_stopped), status == "STOPPED") { status = "STOPPED" }
                    KindButton(stringResource(R.string.status_fault), status == "FAULT") { status = "FAULT" }
                }
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it },
                    label = { Text(stringResource(R.string.visit_note)) },
                    singleLine = true,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.photos_label) + " (" + photos.size + ")",
                    style = MaterialTheme.typography.labelMedium,
                )
                if (photos.isEmpty()) {
                    Text(
                        text = stringResource(R.string.no_photos),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    photos.forEach { photo ->
                        Text(
                            text = File(photo.filePath).name,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                OutlinedButton(
                    onClick = onAddPhoto,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.add_photo))
                }
            }
        },
        confirmButton = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = onDelete) {
                    Text(
                        text = stringResource(R.string.equipment_delete_title),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                TextButton(
                    onClick = {
                        onSave(
                            entity.copy(
                                runningHours = hours.toDoubleOrNull(),
                                pressureBar = pressure.toDoubleOrNull(),
                                status = status,
                                note = note,
                            ),
                        )
                    },
                ) {
                    Text(stringResource(R.string.save))
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.cancel))
            }
        },
    )
}

@Composable
private fun KindButton(label: String, selected: Boolean, onClick: () -> Unit) {
    if (selected) {
        Button(onClick = onClick, modifier = Modifier.padding(end = 8.dp)) {
            Text(label, maxLines = 1)
        }
    } else {
        OutlinedButton(onClick = onClick, modifier = Modifier.padding(end = 8.dp)) {
            Text(label, maxLines = 1)
        }
    }
}

@Composable
private fun statusLabel(status: String): String = when (status) {
    "RUNNING" -> stringResource(R.string.status_running)
    "STOPPED" -> stringResource(R.string.status_stopped)
    else -> stringResource(R.string.status_fault)
}

private fun sharePackage(context: Context, file: File) {
    val uri = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "application/zip"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    context.startActivity(Intent.createChooser(intent, null))
}

private data class CameraTarget(val type: String, val ref: String)

// ===================== صور الزيارة =====================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VisitPhotosScreen(
    photos: List<VisitPhotoEntity>,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    var preview by remember { mutableStateOf<VisitPhotoEntity?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.photos_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = stringResource(R.string.nav_back),
                        )
                    }
                },
            )
        },
    ) { padding ->
        if (photos.isEmpty()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = stringResource(R.string.photos_empty),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(photos, key = { it.id }) { photo ->
                    PhotoGridItem(photo = photo, onClick = { preview = photo })
                }
            }
        }
    }

    preview?.let { photo ->
        AlertDialog(
            onDismissRequest = { preview = null },
            title = { Text(File(photo.filePath).name) },
            text = {
                val bitmap = remember(photo.id) { loadThumbnail(photo.filePath, 1024) }
                if (bitmap != null) {
                    Image(
                        bitmap = bitmap.asImageBitmap(),
                        contentDescription = null,
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(max = 420.dp),
                        contentScale = ContentScale.Fit,
                    )
                } else {
                    Text(stringResource(R.string.photos_empty))
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val file = File(photo.filePath)
                        if (file.exists()) {
                            sharePhoto(context, file)
                        }
                    },
                ) {
                    Text(stringResource(R.string.photos_share))
                }
            },
            dismissButton = {
                TextButton(onClick = { preview = null }) {
                    Text(stringResource(R.string.close))
                }
            },
        )
    }
}

@Composable
private fun PhotoGridItem(photo: VisitPhotoEntity, onClick: () -> Unit) {
    Card(modifier = Modifier.clickable(onClick = onClick)) {
        Column {
            val bitmap = remember(photo.id) { loadThumbnail(photo.filePath, 512) }
            if (bitmap != null) {
                Image(
                    bitmap = bitmap.asImageBitmap(),
                    contentDescription = null,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp),
                    contentScale = ContentScale.Crop,
                )
            } else {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp),
                )
            }
            Text(
                text = photo.takenAt.replace('T', ' ').take(16),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(6.dp),
            )
        }
    }
}

private fun loadThumbnail(path: String, targetPx: Int): Bitmap? = try {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(path, bounds)
    var sample = 1
    while (bounds.outWidth / sample > targetPx * 2 || bounds.outHeight / sample > targetPx * 2) {
        sample *= 2
    }
    BitmapFactory.decodeFile(path, BitmapFactory.Options().apply { inSampleSize = sample })
} catch (e: Exception) {
    null
}

private fun sharePhoto(context: Context, file: File) {
    val uri = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "image/jpeg"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, null))
}

// ===================== سجل الزيارات =====================

private data class VisitHistoryItem(
    val visit: VisitEntity,
    val locationName: String,
    val equipmentCount: Int,
    val issueCount: Int,
    val photoCount: Int,
    val packageFile: File?,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VisitsHistoryScreen(
    visitRepository: VisitRepository,
    hierarchyRepository: HierarchyRepository,
    onOpenVisit: (Long) -> Unit,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    var loading by remember { mutableStateOf(true) }
    var visitItems by remember { mutableStateOf<List<VisitHistoryItem>>(emptyList()) }
    var showPackageMissing by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val data = hierarchyRepository.data.first()
        val tree = TreeBuilder.build(data.projects, data.regions, data.zones, data.locations)
        val nameByCode = mutableMapOf<String, String>()
        fun walk(nodes: List<TreeNode>) {
            for (node in nodes) {
                nameByCode[node.code] = node.name
                walk(node.children)
            }
        }
        walk(tree)

        val visits = visitRepository.allVisitsOnce()
        visitItems = visits.map { visit ->
            VisitHistoryItem(
                visit = visit,
                locationName = nameByCode[visit.locationCode] ?: visit.locationCode,
                equipmentCount = visitRepository.equipmentCountOnce(visit.id),
                issueCount = visitRepository.issueCountOnce(visit.id),
                photoCount = visitRepository.photoCountOnce(visit.id),
                packageFile = visit.packageName?.let { name ->
                    File(File(context.getExternalFilesDir(null), "packages"), name).takeIf { it.exists() }
                },
            )
        }
        loading = false
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.visits_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = stringResource(R.string.nav_back),
                        )
                    }
                },
            )
        },
    ) { padding ->
        when {
            loading -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                CircularProgressIndicator()
            }
            visitItems.isEmpty() -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = stringResource(R.string.visits_empty),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
            else -> LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
            ) {
                items(visitItems, key = { it.visit.id }) { item ->
                    VisitHistoryCard(
                        item = item,
                        onResume = { onOpenVisit(item.visit.id) },
                        onShare = { file -> sharePackage(context, file) },
                        onMissing = { showPackageMissing = true },
                    )
                }
            }
        }
    }

    if (showPackageMissing) {
        AlertDialog(
            onDismissRequest = { showPackageMissing = false },
            title = { Text(stringResource(R.string.visit_share_package)) },
            text = { Text(stringResource(R.string.visit_package_missing)) },
            confirmButton = {
                TextButton(onClick = { showPackageMissing = false }) {
                    Text(stringResource(R.string.done))
                }
            },
        )
    }
}

@Composable
private fun VisitHistoryCard(
    item: VisitHistoryItem,
    onResume: () -> Unit,
    onShare: (File) -> Unit,
    onMissing: () -> Unit,
) {
    val visit = item.visit
    val exported = visit.status == "EXPORTED"
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = item.locationName,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = stringResource(
                        if (exported) R.string.visit_status_exported else R.string.visit_status_draft,
                    ),
                    style = MaterialTheme.typography.labelMedium,
                    color = if (exported) Color(0xFF2E7D32) else Color(0xFFB26A00),
                )
            }
            Text(
                text = visit.visitId + " • " + visit.startedAt.replace('T', ' ').take(16),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.outline,
            )
            Text(
                text = stringResource(
                    R.string.visit_history_stats,
                    item.equipmentCount,
                    item.issueCount,
                    item.photoCount,
                ),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!exported) {
                    Button(onClick = onResume, modifier = Modifier.weight(1f)) {
                        Text(stringResource(R.string.visit_resume))
                    }
                }
                if (exported) {
                    OutlinedButton(
                        onClick = { item.packageFile?.let(onShare) ?: onMissing() },
                        modifier = Modifier.weight(1f),
                    ) {
                        Text(stringResource(R.string.visit_share_package))
                    }
                }
            }
        }
    }
}
