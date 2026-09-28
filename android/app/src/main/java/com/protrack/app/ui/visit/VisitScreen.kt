package com.protrack.app.ui.visit

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
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
import com.protrack.app.data.db.VisitPhotoEntity
import com.protrack.app.domain.ChecklistCatalog
import com.protrack.app.ui.capture.CameraCaptureScreen
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
) {
    val viewModel: VisitViewModel = viewModel(
        factory = VisitViewModel.Factory(hierarchyRepository, visitRepository, photoManager, exporter),
    )
    val step by viewModel.step.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val outcome by viewModel.exportOutcome.collectAsState()
    val photos by viewModel.photos.collectAsState()
    var notes by rememberSaveable { mutableStateOf("") }

    val context = LocalContext.current
    var cameraTargetRef by remember { mutableStateOf<String?>(null) }
    var pendingCameraRef by remember { mutableStateOf<String?>(null) }
    var showPermissionMessage by remember { mutableStateOf(false) }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        if (result[Manifest.permission.CAMERA] == true) {
            cameraTargetRef = pendingCameraRef
        } else {
            showPermissionMessage = true
        }
        pendingCameraRef = null
    }

    val startCapture: (String) -> Unit = { ref ->
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
        if (granted) {
            cameraTargetRef = ref
        } else {
            pendingCameraRef = ref
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.CAMERA,
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                ),
            )
        }
    }

    val activeCameraRef = cameraTargetRef
    if (activeCameraRef != null) {
        CameraCaptureScreen(
            onCaptured = { file ->
                viewModel.attachPhoto("EQUIPMENT", activeCameraRef, file)
                cameraTargetRef = null
            },
            onCancel = { cameraTargetRef = null },
            fileFactory = { viewModel.newPhotoFile() ?: File(context.filesDir, "photo.jpg") },
        )
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
                    VisitViewModel.Step.LOCATION -> LocationStep(viewModel)
                    VisitViewModel.Step.EQUIPMENT -> EquipmentStep(
                        viewModel = viewModel,
                        photos = photos,
                        onAddPhoto = startCapture,
                    )
                    VisitViewModel.Step.CHECKLIST -> ChecklistStep(viewModel)
                    VisitViewModel.Step.REVIEW -> ReviewStep(
                        viewModel = viewModel,
                        notes = notes,
                        onNotesChange = { notes = it },
                        busy = busy,
                        outcome = outcome,
                        photosCount = photos.size,
                    )
                }
            }
            StepNavBar(
                viewModel = viewModel,
                step = step,
                busy = busy,
                outcome = outcome,
                notes = notes,
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
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
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
private fun LocationStep(viewModel: VisitViewModel) {
    val options by viewModel.locationOptions.collectAsState()
    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            text = stringResource(R.string.visit_select_location),
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(16.dp),
        )
        if (options.isEmpty()) {
            Text(
                text = stringResource(R.string.visit_no_locations),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(16.dp),
            )
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(options, key = { it.code }) { option ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { viewModel.chooseLocation(option.code) }
                            .padding(horizontal = 16.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(option.name, style = MaterialTheme.typography.bodyLarge)
                            Text(
                                text = option.path,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Text(
                                text = option.code,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.outline,
                            )
                        }
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                            contentDescription = null,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun EquipmentStep(
    viewModel: VisitViewModel,
    photos: List<VisitPhotoEntity>,
    onAddPhoto: (String) -> Unit,
) {
    val equipment by viewModel.equipment.collectAsState()
    var showAdd by remember { mutableStateOf(false) }
    var editTarget by remember { mutableStateOf<VisitEquipmentEntity?>(null) }

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
                onAddPhoto("${entity.kind}-${entity.tag}")
                editTarget = null
            },
            onDismiss = { editTarget = null },
            onSave = { updated ->
                viewModel.updateEquipment(updated)
                editTarget = null
            },
        )
    }
}

@Composable
private fun ChecklistStep(viewModel: VisitViewModel) {
    val checklist by viewModel.checklist.collectAsState()
    LazyColumn(modifier = Modifier.fillMaxSize()) {
        items(checklist, key = { it.id }) { item ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = ChecklistCatalog.nameFor(item.itemCode),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text(
                        text = item.itemCode,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
                ChecklistStatusButton(status = item.status) { viewModel.cycleChecklist(item) }
            }
        }
    }
}

@Composable
private fun ChecklistStatusButton(status: String, onClick: () -> Unit) {
    val label = when (status) {
        "OK" -> stringResource(R.string.chk_ok)
        "MINOR" -> stringResource(R.string.chk_minor)
        else -> stringResource(R.string.chk_fault)
    }
    val color = when (status) {
        "OK" -> MaterialTheme.colorScheme.primary
        "MINOR" -> Color(0xFFB26A00)
        else -> MaterialTheme.colorScheme.error
    }
    Button(
        onClick = onClick,
        colors = ButtonDefaults.buttonColors(containerColor = color),
    ) {
        Text(label)
    }
}

@Composable
private fun ReviewStep(
    viewModel: VisitViewModel,
    notes: String,
    onNotesChange: (String) -> Unit,
    busy: Boolean,
    outcome: ExportOutcome?,
    photosCount: Int,
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
        visit?.let {
            Text(
                text = stringResource(R.string.visit_location_label, it.locationCode),
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
