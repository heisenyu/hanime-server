import {createRouter, createWebHistory, RouteRecordRaw} from 'vue-router';
import HomePage from "../components/HomePage.vue";
import videoDetailPage from "../components/VideoDetailPage.vue";
import CalendarPage from "../components/CalendarPage.vue";
import SearchPage from "../components/SearchPage.vue";


const routes: Array<RouteRecordRaw> = [
    {
        path: '/',
        name: 'Home',
        component: HomePage
    },
    {
        path: '/video/:id',
        name: 'VideoDetail',
        component: videoDetailPage
    },
    {
        path: '/calendar',
        name: 'Calendar',
        component: CalendarPage
    },
    {
        path: '/search',
        name: 'Search',
        component: SearchPage
    },
    {
        path: '/downloads',
        name: 'Downloads',
        component: () => import('../views/Downloads.vue')
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('../views/NotFound.vue')
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior() {
        // 始终滚动到顶部
        return { top: 0 };
    }
});

export default router; 