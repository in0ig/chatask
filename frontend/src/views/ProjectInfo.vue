<script setup lang="ts">
import { ref } from 'vue';

interface Project {
  id: number;
  name: string;
  createdAt: string;
  description: string;
}

const projects = ref<Project[]>([
  {
    id: 1,
    name: '销售数据分析',
    createdAt: '2026-01-15',
    description: '分析月度销售趋势和客户行为'
  },
  {
    id: 2,
    name: '库存管理',
    createdAt: '2026-01-10',
    description: '监控库存水平和补货需求'
  },
  {
    id: 3,
    name: '财务报表',
    createdAt: '2026-01-05',
    description: '生成月度财务报告和预算分析'
  }
]);

const newProjectName = ref('');
const newProjectDescription = ref('');

function addProject() {
  if (newProjectName.value.trim()) {
    projects.value.push({
      id: Date.now(),
      name: newProjectName.value.trim(),
      createdAt: new Date().toISOString().split('T')[0],
      description: newProjectDescription.value.trim()
    });
    newProjectName.value = '';
    newProjectDescription.value = '';
  }
}

function deleteProject(id: number) {
  projects.value = projects.value.filter(p => p.id !== id);
}
</script>

<template>
  <div class="project-info-container">
    <div class="header">
      <h1>项目管理</h1>
      <div class="add-project-form">
        <input
          v-model="newProjectName"
          placeholder="项目名称"
          class="project-name-input"
        />
        <input
          v-model="newProjectDescription"
          placeholder="项目描述"
          class="project-description-input"
        />
        <button @click="addProject" class="add-button">添加项目</button>
      </div>
    </div>

    <div class="projects-grid">
      <div 
        v-for="project in projects" 
        :key="project.id" 
        class="project-card"
      >
        <div class="project-header">
          <h3>{{ project.name }}</h3>
          <button @click="deleteProject(project.id)" class="delete-button">删除</button>
        </div>
        <p class="project-date">创建时间: {{ project.createdAt }}</p>
        <p class="project-description">{{ project.description }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.project-info-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.header h1 {
  color: #333;
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.add-project-form {
  display: flex;
  gap: 12px;
  align-items: center;
}

.project-name-input,
.project-description-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 150px;
}

.add-button {
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.add-button:hover {
  background-color: #0c7bd7;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.project-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.project-header h3 {
  color: #333;
  font-size: 18px;
  font-weight: 500;
  margin: 0;
}

.delete-button {
  background-color: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.delete-button:hover {
  background-color: #d9363e;
}

.project-date {
  color: #666;
  font-size: 13px;
  margin: 8px 0;
}

.project-description {
  color: #555;
  font-size: 14px;
  line-height: 1.5;
}
</style>