/**
 * Admin Tabulator tables for content hub entities.
 */
(function () {
  if (typeof Tabulator === "undefined") {
    return;
  }

  const tables = {};

  function initArticlesTable() {
    if (tables.articles) return tables.articles;
    const table = new Tabulator("#manage-articles-table", {
      ...advancedTableConfig,
      ajaxURL: "/features/community/content/api/articles",
      ajaxResponse: standardAjaxResponse,
      columns: [
        { title: "Title", field: "title", headerFilter: "input", minWidth: 200 },
        { title: "Category", field: "category", headerFilter: "input", width: 140 },
        { title: "Published", field: "published_at", formatter: formatTimestamp, width: 160 },
        {
          title: "Actions",
          field: "actions",
          width: 120,
          headerSort: false,
          formatter(cell) {
            const rowData = cell.getRow().getData();
            return createRowCrudButtons(rowData, {
              onEdit: "editArticle",
              onDelete: "deleteArticle",
            });
          },
        },
      ],
    });
    tables.articles = table;
    bindRowActionHandlers("#manage-articles-table", { onEdit: "editArticle", onDelete: "deleteArticle" });
    return table;
  }

  function initPodcastsTable() {
    if (tables.podcasts) return tables.podcasts;
    const table = new Tabulator("#manage-podcasts-table", {
      ...advancedTableConfig,
      ajaxURL: "/features/community/content/api/podcasts",
      ajaxResponse: standardAjaxResponse,
      columns: [
        { title: "Title", field: "title", headerFilter: "input", minWidth: 200 },
        { title: "Host", field: "host", headerFilter: "input", width: 160 },
        { title: "Published", field: "published_at", formatter: formatTimestamp, width: 160 },
        {
          title: "Actions",
          field: "actions",
          width: 120,
          headerSort: false,
          formatter(cell) {
            const rowData = cell.getRow().getData();
            return createRowCrudButtons(rowData, {
              onEdit: "editPodcast",
              onDelete: "deletePodcast",
            });
          },
        },
      ],
    });
    tables.podcasts = table;
    bindRowActionHandlers("#manage-podcasts-table", { onEdit: "editPodcast", onDelete: "deletePodcast" });
    return table;
  }

  function initVideosTable() {
    if (tables.videos) return tables.videos;
    const table = new Tabulator("#manage-videos-table", {
      ...advancedTableConfig,
      ajaxURL: "/features/community/content/api/videos",
      ajaxResponse: standardAjaxResponse,
      columns: [
        { title: "Title", field: "title", headerFilter: "input", minWidth: 200 },
        { title: "Category", field: "category", headerFilter: "input", width: 140 },
        { title: "Duration (min)", field: "duration_minutes", width: 140 },
        {
          title: "Actions",
          field: "actions",
          width: 120,
          headerSort: false,
          formatter(cell) {
            const rowData = cell.getRow().getData();
            return createRowCrudButtons(rowData, {
              onEdit: "editVideo",
              onDelete: "deleteVideo",
            });
          },
        },
      ],
    });
    tables.videos = table;
    bindRowActionHandlers("#manage-videos-table", { onEdit: "editVideo", onDelete: "deleteVideo" });
    return table;
  }

  function initNewsTable() {
    if (tables.news) return tables.news;
    const table = new Tabulator("#manage-news-table", {
      ...advancedTableConfig,
      ajaxURL: "/features/community/content/api/news",
      ajaxResponse: standardAjaxResponse,
      columns: [
        { title: "Headline", field: "headline", headerFilter: "input", minWidth: 220 },
        { title: "Source", field: "source", headerFilter: "input", width: 140 },
        { title: "Published", field: "publish_date", formatter: formatTimestamp, width: 160 },
        {
          title: "Actions",
          field: "actions",
          width: 120,
          headerSort: false,
          formatter(cell) {
            const rowData = cell.getRow().getData();
            return createRowCrudButtons(rowData, {
              onEdit: "editNews",
              onDelete: "deleteNews",
            });
          },
        },
      ],
    });
    tables.news = table;
    bindRowActionHandlers("#manage-news-table", { onEdit: "editNews", onDelete: "deleteNews" });
    return table;
  }

  function initTab(target) {
    switch (target) {
      case "articles":
        initArticlesTable();
        break;
      case "podcasts":
        initPodcastsTable();
        break;
      case "videos":
        initVideosTable();
        break;
      case "news":
        initNewsTable();
        break;
      default:
        break;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const manageNav = document.querySelectorAll("[data-manage-tab]");
    manageNav.forEach((link) => {
      link.addEventListener("shown.bs.tab", (e) => {
        const target = e.target.getAttribute("data-manage-tab");
        initTab(target);
      });
    });
    // Init first table when Manage tab is shown
    const manageTabLink = document.querySelector('a[href="#content-manage"]');
    if (manageTabLink) {
      manageTabLink.addEventListener("shown.bs.tab", () => initTab("articles"));
    }
  });

  document.body.addEventListener("refreshContentTables", () => {
    Object.values(tables).forEach((table) => {
      if (table && typeof table.replaceData === "function") {
        table.replaceData();
      }
    });
  });

  // Edit/Delete handlers
  window.editArticle = function editArticle(id) {
    editTabulatorRow(`/features/community/content/partials/article_form?content_id=${id}`);
  };
  window.deleteArticle = function deleteArticle(id) {
    deleteTabulatorRow(`/features/community/content/api/articles/${id}`, "#manage-articles-table", {
      title: "Delete Article",
      message: "Delete this article?",
      confirmText: "Delete",
    });
  };

  window.editPodcast = function editPodcast(id) {
    editTabulatorRow(`/features/community/content/partials/podcast_form?episode_id=${id}`);
  };
  window.deletePodcast = function deletePodcast(id) {
    deleteTabulatorRow(`/features/community/content/api/podcasts/${id}`, "#manage-podcasts-table", {
      title: "Delete Podcast",
      message: "Delete this podcast episode?",
      confirmText: "Delete",
    });
  };

  window.editVideo = function editVideo(id) {
    editTabulatorRow(`/features/community/content/partials/video_form?video_id=${id}`);
  };
  window.deleteVideo = function deleteVideo(id) {
    deleteTabulatorRow(`/features/community/content/api/videos/${id}`, "#manage-videos-table", {
      title: "Delete Video",
      message: "Delete this video?",
      confirmText: "Delete",
    });
  };

  window.editNews = function editNews(id) {
    editTabulatorRow(`/features/community/content/partials/news_form?news_id=${id}`);
  };
  window.deleteNews = function deleteNews(id) {
    deleteTabulatorRow(`/features/community/content/api/news/${id}`, "#manage-news-table", {
      title: "Delete News",
      message: "Delete this news item?",
      confirmText: "Delete",
    });
  };
})();
