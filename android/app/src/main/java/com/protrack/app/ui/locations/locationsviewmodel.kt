package com.protrack.app.ui.locations

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.TreeBuilder
import com.protrack.app.domain.TreeRow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class LocationsUiState(
    val rows: List<TreeRow> = emptyList(),
    val loading: Boolean = true,
)

class LocationsViewModel(private val repository: HierarchyRepository) : ViewModel() {

    private val expanded = MutableStateFlow<Set<String>>(emptySet())

    val uiState: StateFlow<LocationsUiState> =
        combine(repository.data, expanded) { data, expandedCodes ->
            val tree = TreeBuilder.build(data.projects, data.regions, data.zones, data.locations)
            LocationsUiState(
                rows = TreeBuilder.flatten(tree, expandedCodes),
                loading = false,
            )
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), LocationsUiState())

    fun toggleExpanded(code: String) {
        expanded.value = if (code in expanded.value) expanded.value - code else expanded.value + code
    }

    fun addNode(type: NodeType, name: String, parentCode: String?) {
        viewModelScope.launch { repository.addNode(type, name, parentCode) }
    }

    fun rename(type: NodeType, code: String, name: String) {
        viewModelScope.launch { repository.rename(type, code, name) }
    }

    fun setStatus(type: NodeType, code: String, status: String) {
        viewModelScope.launch { repository.setStatus(type, code, status) }
    }

    class Factory(private val repository: HierarchyRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return LocationsViewModel(repository) as T
        }
    }
}
