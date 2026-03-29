# adwords_fn

data_dir <-
  function(client = 'Only The Glass',
           g = c('CA-ON', 'CA', 'US', 'UK')) {
    for (i in g)
    {
      if (dir.exists(paste0("data/", tolower(gsub(
        "[[:blank:]]", "-", client
      )), "/", tolower(i))))
        DATA_DIR <<- 1
      else
      {
        dir.create(path = paste0("data/", tolower(gsub(
          "[[:blank:]]", "-", client
        )), "/", tolower(i)),
        recursive = T)
        DATA_DIR <<- 1
      }
    }
  }
seo_keywords <-
  function(terms, g = 'US', client = 'Only The Glass') {
    terms %>% tibble(keywords = .) %>%
      mutate(
        trend_all = map(.x = keywords,  ~ {
          gtrends(.x,
                  time = paste("2010-04-01", Sys.Date()),
                  geo = g)
        }),
        interest = map2(.x = trend_all, .y = keywords,  ~ {
          #Determine if the interest information exists from the gtrends call
          if (!is.null(.x[['interest_over_time']]))
            .x[['interest_over_time']] %>% mutate_all(as.character)
          else
          {
            #Determine if the no interest array does not exist
            if (!file.exists(paste0(
              "data/",
              tolower(gsub("[[:blank:]]", "-", client)),
              "/",
              tolower(g),
              "/no-interest.RDS"
            )) & DATA_DIR > 0)
              saveRDS(
                object = .y,
                file = paste0(
                  "data/",
                  tolower(gsub("[[:blank:]]", "-", client)),
                  "/",
                  tolower(g),
                  "/no-interest.RDS"
                )
              )
            else
            {
              #If the file exists, append the keyword without interest over time data
              ni <-
                readRDS(paste0(
                  "data/",
                  tolower(gsub("[[:blank:]]", "-", client)),
                  "/",
                  tolower(g),
                  "/no-interest.RDS"
                ))
              ni <- append(ni, .y)
              saveRDS(
                object = ni,
                file = paste0(
                  "data/",
                  tolower(gsub("[[:blank:]]", "-", client)),
                  "/",
                  tolower(g),
                  "/no-interest.RDS"
                )
              )
              
            }
          }
          
        }),
        related = map2(.x = trend_all, .y = keywords, ~ {
          if (!is.null(.x[['related_queries']]))
            .x[['related_queries']] %>% mutate_all(as.character)
          else
          {
            #Determine if the no related queries array does not exist
            if (!file.exists(paste0(
              "data/",
              tolower(gsub("[[:blank:]]", "-", client)),
              "/",
              tolower(g),
              "/no-related-queries.RDS"
            )) & DATA_DIR > 0)
              saveRDS(
                object = .y,
                file = paste0(
                  "data/",
                  tolower(gsub("[[:blank:]]", "-", client)),
                  "/",
                  tolower(g),
                  "/no-related-queries.RDS"
                )
              )
            else
            {
              #If the file exists, append the keyword without related queries data
              nr <-
                readRDS(paste0(
                  "data/",
                  tolower(gsub("[[:blank:]]", "-", client)),
                  "/",
                  tolower(g),
                  "/no-related-queries.RDS"
                ))
              nr <- append(nr, .y)
              saveRDS(
                object = nr,
                file = paste0(
                  "data/",
                  tolower(gsub("[[:blank:]]", "-", client)),
                  "/",
                  tolower(g),
                  "/no-related-queries.RDS"
                )
              )
              
            }
          }
        }),
        lm_all = map(.x = interest,  ~ {
          if (!is.null(.x))
            lm(formula = as.numeric(hits) ~ as.Date(date) , data = .x)
        }),
        lm_tidy = map(.x = lm_all,  ~ {
          if (!is.null(.x))
            broom::tidy(.x)
        })
      ) %>% return(.)
  }


seo_trends <- function(df,
                       xl = "Date (since 2010)",
                       yl = "Hits",
                       titlel = "Trends for Onlytheglass.ca",
                       cap = "Source: Google Trends - Canada",
                       cols = 1) {
  # browser()
  #loading the necessary libraries
  require(magrittr, quietly = T)
  require(RColorBrewer, quietly = T)
  require(ggthemes, quietly = T)
  #Test that the data is useable for trends and has all essential fields
  stopifnot(exprs = sum(c('date', 'hits', 'keyword') %in% colnames(df)) >= 3)
  
  #Determining the number of colours necessary for the color palette
  n <- nrow(df)
  qual_col_pals = brewer.pal.info[brewer.pal.info$category == 'qual',]
  col_vector = unlist(mapply(
    brewer.pal,
    qual_col_pals$maxcolors,
    rownames(qual_col_pals)
  ))
  
  
  #Get the data
  df %>%
    ggplot(aes(date, hits, colour = keyword)) +
    geom_area(aes(color = keyword, fill = keyword),
              alpha = 0.5,
              position = position_dodge(0.8)) +
    labs(
      x = xl,
      y = yl,
      title = titlel,
      caption = cap
    ) +
    ggthemes::theme_tufte() +
    theme(
      axis.title.y = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.y = element_blank()
    ) +
    geom_smooth(
      method = "lm",
      se = FALSE,
      color = "black",
      formula = y ~ x
    ) +
    scale_fill_manual(values = sample(col_vector, size = length(unique(df$keywords)))) +
    facet_wrap(~ keyword, ncol = cols) +
    guides(legend = F,
           fill = F,
           colour = F) -> p
  
  return(p)
}

keyword_performance <- function()
{
  
}