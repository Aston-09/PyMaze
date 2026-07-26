import React from 'react';
import './Sidebar.css';

const CHAPTERS = [
  {
    id: 'ch0',
    title: 'Chapter 0: The Awakening',
    scenes: ['awakening']
  },
  {
    id: 'ch1',
    title: 'Chapter 1: The First Steps',
    scenes: ['chapter_1_dragon', 'chapter_1_dragon_trial', 'chapter_1_trial_failed', 'chapter_1b_wisdom_of_system']
  },
  {
    id: 'ch2',
    title: 'Chapter 2: Windstorm Triage',
    scenes: ['chapter_2_trial_of_choice']
  },
  {
    id: 'ch3',
    title: 'Chapter 3: The Depths',
    scenes: []
  }
];

export default function Sidebar({ player }) {
  if (!player) return null;

  // Determine which chapter is active based on current_scene
  let activeChapterIndex = -1;
  const currentScene = player.current_scene;

  for (let i = 0; i < CHAPTERS.length; i++) {
    if (CHAPTERS[i].scenes.includes(currentScene)) {
      activeChapterIndex = i;
      break;
    }
  }

  // If the scene isn't found, default to 0 if it's new
  if (activeChapterIndex === -1 && currentScene) {
      activeChapterIndex = 0;
  }

  return (
    <aside className="sidebar fade-in">
      <h2 className="sidebar-title">Journey</h2>
      <ul className="chapter-list">
        {CHAPTERS.map((chapter, index) => {
          let statusClass = 'coming-soon';
          let statusText = 'Coming Soon';

          if (activeChapterIndex !== -1) {
            if (index < activeChapterIndex) {
              statusClass = 'completed';
              statusText = 'Completed';
            } else if (index === activeChapterIndex) {
              statusClass = 'in-progress';
              statusText = 'In Progress';
            }
          }

          return (
            <li key={chapter.id} className={`chapter-item ${statusClass}`}>
              <div className="chapter-marker" />
              <div className="chapter-title">{chapter.title}</div>
              <div className="chapter-status">{statusText}</div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
