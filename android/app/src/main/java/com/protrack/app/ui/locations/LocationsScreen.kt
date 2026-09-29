package com.protrack.app.ui.locations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.protrack.app.R
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.TreeNode
import com.protrack.app.domain.TreeRow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocationsScreen(
    repository: HierarchyRepository,
    onBack: () -> Unit,
    autoAddUnder: String? = null,
) {
    val viewModel: LocationsViewModel = viewModel(factory = LocationsViewModel.Factory(repository))
    val state by viewModel.uiState.collectAsState()
    val deleteResult by viewModel.deleteResult.collectAsState()

    var showAddProject by remember { mutableStateOf(false) }
    var actionNode by remember { mutableStateOf<TreeNode?>(null) }
    var editTarget by remember { mutableStateOf<EditTarget?>(null) }
    var deleteAskNode by remember { mutableStateOf<TreeNode?>(null) }
    var autoAddHandled by remember { mutableStateOf(false) }
    var autoAddParent by remember { mutableStateOf<TreeNode?>(null) }

    // الوصول التلقائي من «زيارة جديدة»: افتح إضافة العنصر التابع مباشرة (مع اختيار النوع عند تعدد الخيارات)
    LaunchedEffect(autoAddUnder) {
        if (!autoAddUnder.isNullOrBlank() && !autoAddHandled) {
            autoAddHandled = true
            val node = viewModel.findNode(autoAddUnder)
            if (node != null) {
                val types = addableChildTypes(node.type)
                when (types.size) {
                    0 -> Unit
                    1 -> editTarget = EditTarget.AddChild(parent = node, childType = types[0])
                    else -> autoAddParent = node
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.locations_title)) },
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
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddProject = true }) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = stringResource(R.string.add_project),
                )
            }
        },
    ) { padding ->
        when {
            state.loading -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    CircularProgressIndicator()
                }
            }
            state.rows.isEmpty() -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = stringResource(R.string.empty_tree),
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center,
                    )
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                ) {
                    items(state.rows, key = { it.node.type.name + ":" + it.node.code }) { row ->
                        TreeRowItem(
                            row = row,
                            onToggle = { viewModel.toggleExpanded(row.node.code) },
                            onActions = { actionNode = row.node },
                        )
                    }
                }
            }
        }
    }

    if (showAddProject) {
        NameDialog(
            title = stringResource(R.string.add_project),
            initialValue = "",
            onDismiss = { showAddProject = false },
            onConfirm = { name ->
                viewModel.addNode(NodeType.PROJECT, name, null)
                showAddProject = false
            },
        )
    }

    actionNode?.let { node ->
        ActionsDialog(
            node = node,
            onDismiss = { actionNode = null },
            onAddChild = { childType ->
                editTarget = EditTarget.AddChild(parent = node, childType = childType)
                actionNode = null
            },
            onRename = {
                editTarget = EditTarget.Rename(node = node)
                actionNode = null
            },
            onToggleStatus = {
                val newStatus = if (node.status == "ACTIVE") "INACTIVE" else "ACTIVE"
                viewModel.setStatus(node.type, node.code, newStatus)
                actionNode = null
            },
            onDelete = {
                deleteAskNode = node
                actionNode = null
            },
        )
    }

    deleteAskNode?.let { node ->
        AlertDialog(
            onDismissRequest = { deleteAskNode = null },
            title = { Text(stringResource(R.string.delete)) },
            text = { Text(stringResource(R.string.delete_node_confirm, node.name)) },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.deleteNode(node)
                        deleteAskNode = null
                    },
                ) {
                    Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteAskNode = null }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }

    deleteResult?.let { reason ->
        AlertDialog(
            onDismissRequest = { viewModel.clearDeleteResult() },
            title = { Text(stringResource(R.string.delete)) },
            text = {
                Text(
                    when (reason) {
                        "children" -> stringResource(R.string.delete_blocked_children)
                        else -> stringResource(R.string.delete_blocked_visits)
                    },
                )
            },
            confirmButton = {
                TextButton(onClick = { viewModel.clearDeleteResult() }) {
                    Text(stringResource(R.string.done))
                }
            },
        )
    }

    editTarget?.let { target ->
        val title = when (target) {
            is EditTarget.AddChild -> stringResource(titleResFor(target.childType))
            is EditTarget.Rename -> stringResource(R.string.rename)
        }
        NameDialog(
            title = title,
            initialValue = if (target is EditTarget.Rename) target.node.name else "",
            onDismiss = { editTarget = null },
            onConfirm = { name ->
                when (target) {
                    is EditTarget.AddChild -> viewModel.addNode(target.childType, name, target.parent.code)
                    is EditTarget.Rename -> viewModel.rename(target.node.type, target.node.code, name)
                }
                editTarget = null
            },
        )
    }

    autoAddParent?.let { parent ->
        AlertDialog(
            onDismissRequest = { autoAddParent = null },
            title = { Text(parent.name) },
            text = {
                Column {
                    addableChildTypes(parent.type).forEach { type ->
                        TextButton(
                            onClick = {
                                editTarget = EditTarget.AddChild(parent = parent, childType = type)
                                autoAddParent = null
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text(stringResource(titleResFor(type)))
                        }
                    }
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { autoAddParent = null }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }
}

private sealed interface EditTarget {
    data class AddChild(val parent: TreeNode, val childType: NodeType) : EditTarget
    data class Rename(val node: TreeNode) : EditTarget
}

private fun titleResFor(type: NodeType): Int = when (type) {
    NodeType.PROJECT -> R.string.add_project
    NodeType.REGION -> R.string.add_region
    NodeType.ZONE -> R.string.add_zone
    NodeType.LOCATION -> R.string.add_location
}

/** أنواع العناصر المسموح إضافتها تحت نوع معيّن (مع تخطي مستويات ناقصة). */
private fun addableChildTypes(type: NodeType): List<NodeType> = when (type) {
    NodeType.PROJECT -> listOf(NodeType.REGION, NodeType.ZONE, NodeType.LOCATION)
    NodeType.REGION -> listOf(NodeType.ZONE, NodeType.LOCATION)
    NodeType.ZONE -> listOf(NodeType.LOCATION)
    NodeType.LOCATION -> emptyList()
}

@Composable
private fun TreeRowItem(
    row: TreeRow,
    onToggle: () -> Unit,
    onActions: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = (12 + row.depth * 16).dp, end = 4.dp, top = 2.dp, bottom = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (row.hasChildren) {
            IconButton(onClick = onToggle) {
                Icon(
                    imageVector = if (row.expanded) {
                        Icons.Default.KeyboardArrowUp
                    } else {
                        Icons.Default.KeyboardArrowDown
                    },
                    contentDescription = null,
                )
            }
        } else {
            Spacer(modifier = Modifier.size(48.dp))
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = row.node.name,
                style = MaterialTheme.typography.bodyLarge,
            )
            Text(
                text = row.node.code,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Text(
            text = stringResource(
                if (row.node.status == "ACTIVE") R.string.status_active else R.string.status_inactive,
            ),
            style = MaterialTheme.typography.labelMedium,
            color = if (row.node.status == "ACTIVE") {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.outline
            },
        )
        IconButton(onClick = onActions) {
            Icon(
                imageVector = Icons.Default.MoreVert,
                contentDescription = stringResource(R.string.actions),
            )
        }
    }
}

@Composable
private fun ActionsDialog(
    node: TreeNode,
    onDismiss: () -> Unit,
    onAddChild: (NodeType) -> Unit,
    onRename: () -> Unit,
    onToggleStatus: () -> Unit,
    onDelete: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(node.name) },
        text = {
            Column {
                addableChildTypes(node.type).forEach { type ->
                    TextButton(onClick = { onAddChild(type) }, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(titleResFor(type)))
                    }
                }
                TextButton(onClick = onRename, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.rename))
                }
                TextButton(onClick = onToggleStatus, modifier = Modifier.fillMaxWidth()) {
                    Text(
                        stringResource(
                            if (node.status == "ACTIVE") R.string.deactivate else R.string.activate,
                        ),
                    )
                }
                TextButton(onClick = onDelete, modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = stringResource(R.string.delete),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.cancel))
            }
        },
    )
}

@Composable
private fun NameDialog(
    title: String,
    initialValue: String,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var value by remember { mutableStateOf(initialValue) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(
                value = value,
                onValueChange = { value = it },
                label = { Text(stringResource(R.string.dialog_name_label)) },
                singleLine = true,
            )
        },
        confirmButton = {
            TextButton(
                onClick = {
                    if (value.isNotBlank()) {
                        onConfirm(value.trim())
                    }
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
