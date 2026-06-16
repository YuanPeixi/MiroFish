<template>
  <div class="narrative-page">
    <header class="page-header">
      <div>
        <h1>结局协同推理（最小闭环）</h1>
        <p>项目: {{ projectId }}</p>
      </div>
      <div class="actions">
        <button @click="goBack">返回主流程</button>
        <button @click="refreshState">刷新</button>
      </div>
    </header>

    <section class="card">
      <h2>1) 创建初始剧情快照</h2>
      <div class="row">
        <input v-model="snapshotTitle" placeholder="快照标题" />
        <input v-model="snapshotSummary" placeholder="快照摘要" />
      </div>
      <textarea
        v-model="stateJson"
        rows="10"
        spellcheck="false"
        placeholder='{"characters":[],"events":[],"conflicts":[],"goals":[],"causal_links":[],"timeline":[]}'
      />
      <button @click="createSnapshot">保存快照</button>
    </section>

    <section class="card">
      <h2>2) 分支派生与推进</h2>
      <div class="row">
        <select v-model="selectedSnapshotId">
          <option value="">选择源快照</option>
          <option v-for="s in snapshots" :key="s.snapshot_id" :value="s.snapshot_id">
            {{ s.snapshot_id }} · {{ s.title }}
          </option>
        </select>
        <input v-model="branchName" placeholder="新分支名称（可选）" />
        <button @click="deriveBranch">从快照派生分支</button>
      </div>

      <div class="row">
        <select v-model="selectedBranchId">
          <option value="">选择分支</option>
          <option v-for="b in branches" :key="b.branch_id" :value="b.branch_id">
            {{ b.name }} ({{ b.branch_id }})
          </option>
        </select>
        <input v-model="advanceTitle" placeholder="推进标题" />
        <input v-model="advanceSummary" placeholder="推进摘要" />
      </div>
      <textarea
        v-model="deltaEventsJson"
        rows="5"
        spellcheck="false"
        placeholder='[{"name":"新事件","description":"事件描述"}]'
      />
      <button @click="advanceBranch">推进分支</button>
    </section>

    <section class="card">
      <h2>3) 分支评分与结局选择</h2>
      <div class="row">
        <button @click="scoreBranches">计算评分</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>分支</th>
            <th>总分</th>
            <th>连贯性</th>
            <th>角色一致性</th>
            <th>冲突张力</th>
            <th>观赏性</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in ranking" :key="item.branch_id">
            <td>{{ item.name }}</td>
            <td>{{ item.score }}</td>
            <td>{{ item.score_detail?.coherence }}</td>
            <td>{{ item.score_detail?.character_consistency }}</td>
            <td>{{ item.score_detail?.conflict_tension }}</td>
            <td>{{ item.score_detail?.watchability }}</td>
            <td><button @click="selectEnding(item.branch_id)">选为结局</button></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>4) 导出剧本稿与解释</h2>
      <button @click="exportScript">导出当前结局</button>
      <pre>{{ exported }}</pre>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  advanceNarrativeBranch,
  createNarrativeSnapshot,
  deriveNarrativeBranch,
  exportNarrativeScript,
  getNarrativeState,
  scoreNarrativeBranches,
  selectNarrativeEnding
} from '../api/narrative'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.projectId)

const branches = ref([])
const snapshots = ref([])
const ranking = ref([])
const exported = ref('')

const snapshotTitle = ref('剧情初始快照')
const snapshotSummary = ref('')
const stateJson = ref(JSON.stringify({
  characters: [],
  events: [],
  conflicts: [],
  goals: [],
  causal_links: [],
  timeline: []
}, null, 2))

const selectedSnapshotId = ref('')
const selectedBranchId = ref('')
const branchName = ref('')
const advanceTitle = ref('剧情推进')
const advanceSummary = ref('')
const deltaEventsJson = ref('[]')

const refreshState = async () => {
  const res = await getNarrativeState(projectId.value)
  branches.value = res.data.branches || []
  snapshots.value = res.data.snapshots || []
  if (!selectedSnapshotId.value && snapshots.value.length > 0) {
    selectedSnapshotId.value = snapshots.value[snapshots.value.length - 1].snapshot_id
  }
  if (!selectedBranchId.value && branches.value.length > 0) {
    selectedBranchId.value = branches.value[0].branch_id
  }
}

const createSnapshot = async () => {
  const payload = {
    project_id: projectId.value,
    title: snapshotTitle.value,
    summary: snapshotSummary.value,
    narrative_state: JSON.parse(stateJson.value)
  }
  await createNarrativeSnapshot(payload)
  await refreshState()
}

const deriveBranch = async () => {
  if (!selectedSnapshotId.value) return
  await deriveNarrativeBranch({
    project_id: projectId.value,
    from_snapshot_id: selectedSnapshotId.value,
    branch_name: branchName.value || undefined
  })
  await refreshState()
}

const advanceBranch = async () => {
  if (!selectedBranchId.value) return
  await advanceNarrativeBranch({
    project_id: projectId.value,
    branch_id: selectedBranchId.value,
    title: advanceTitle.value,
    summary: advanceSummary.value,
    delta_events: JSON.parse(deltaEventsJson.value)
  })
  await refreshState()
}

const scoreBranches = async () => {
  const res = await scoreNarrativeBranches({ project_id: projectId.value })
  ranking.value = res.data || []
  await refreshState()
}

const selectEnding = async (branchId) => {
  await selectNarrativeEnding({
    project_id: projectId.value,
    branch_id: branchId
  })
  await refreshState()
}

const exportScript = async () => {
  const res = await exportNarrativeScript(projectId.value)
  exported.value = JSON.stringify(res.data, null, 2)
}

const goBack = () => {
  router.push({ name: 'Process', params: { projectId: projectId.value } })
}

onMounted(refreshState)
</script>

<style scoped>
.narrative-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.actions {
  display: flex;
  gap: 8px;
}

.card {
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 14px;
  background: #fff;
}

.row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

input, select, textarea, button {
  font-size: 14px;
}

input, select, textarea {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 8px;
}

button {
  border: 1px solid #1d4ed8;
  background: #1d4ed8;
  color: #fff;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  border: 1px solid #e5e5e5;
  padding: 8px;
  text-align: left;
}

pre {
  white-space: pre-wrap;
  background: #f8fafc;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  padding: 10px;
  max-height: 360px;
  overflow: auto;
}
</style>
