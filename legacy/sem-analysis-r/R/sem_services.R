#
# 1. Collect the homestars categories
# 2. From the categories, slice all categories into groups of 5 that are then used to scour google trends
# 3. Check out the trends for each of the category groups
# 4. Set a specific time frame for the trends to be analyzed (e.g. upcoming period of marketing (next 3 months))
# 5. Collect the information from the google trends API to determine what's being
#     sought after the most with respect to certain categories by summing the score over the period
# 6. Summarize the categories intermittently and then select the most sought after
#     category in the group of 5 to continue downloading the corresponding information
# remotes::install_github("trendecon/trendecon")
require(trendecon)
require(chatgpt)

categories_original<-readRDS("category_names.RDS")
unused_terms<-readRDS(here::here("data","unused_trends.RDS"))

return_all_catsN <- list()
# return_all_cats[[1]]
for (i in 1:10) {
  if(i==1){
  return_all_catsN[[i]] <-
    ask_chatgpt(
      paste0(
        "I have the following categories of services that people might look for a contractor for:
                   ",
        # paste0(categories_keywords, collapse = "\n"),
        paste0(categories_original, collapse = "\n"),
        "Please return an exhaustive semi-colon separated list (only) of common ways people may search for these services online in a search engine like google. I am expecting a list of more than 500 items",
        "\n\n\n",
        "Do not include the following terms in the list you return:",
        paste0(unused_terms, collapse = "\n"),
        collapse = "\n"
      )
    )
  }else{
    return_all_catsN[[i]] <-
      ask_chatgpt("continue the list of common search terms people might use to find these services using a search engine. Only return semi-colon separated list of services")
  }
}

require(dplyr)
require(magrittr)
# which(grepl("Lawn",categories_keywords))
# which(grepl("Light",categories_keywords))
# categories_keywords[which(grepl("Light",categories_keywords))]
sep_catsN <-
  unique(unlist(lapply(return_all_catsN, function(x)
    trimws(
      gsub("• |[[:punct:]]|[[:digit:]]", "", unlist(strsplit(x, split = ";|\n[[:digit:]]")))
    ))))%>%.[nchar(.)>0]%>%tolower(.)


print(sep_catsN)
# print(sep_cats_all)
# print(sep_cats3)
# # lapply(return_all_cats,function(x)cat(x))
# cat(return_list_cats)
# cat(return_list_cats_1)
# cat(return_list_cats_2)
categories_keywords <- readRDS(here::here("category_names_extended.RDS"))
saveRDS(object = unique(tolower(c(categories_keywords,sep_catsN)))%>%gsub("  "," ",.),here::here("category_names_extended.RDS"))
require(tidyverse)
require(magrittr)
# categories_keywords[which(grepl("Storage", categories_keywords))]
# categories_keywords[sample.int(length(categories_keywords), 1)] -> selected_cats
# print(selected_cats)
# selected_cats %>% strsplit(., split = "/| and | & |, ") %>%
#   unlist(.) -> test_cat
# print(test_cat)
# search_categories <-
#   tibble(categories = c(categories_keywords, "bathroom repair")) %>%
#   dplyr::mutate(search_categories = purrr::map(.x = categories, ~ {
#     # browser()
#     .x %>% strsplit(., split = "/| and | & |, ") %>%
#       unlist(.) %>% c(.x, .) %>% unique(.) -> test_cat
#     #if there's more than one category from the split
#     #find the last item
#     #split the last item's last word
#     # and attach it to the first item
#     #Last item separated
#     if (length(test_cat) > 1) {
#       c(unlist(lapply(test_cat[-length(test_cat)], function(x) {
#         #Determine if there is more than one category
#         if (str_count(test_cat[length(test_cat)], "\\S+") > 1 &
#             #And if the final category is either "Service" or "Repair"
#             (sum(
#               grepl("\\bRepair\\b|\\bService\\b", test_cat[length(test_cat)], fixed = F)
#             ) > 0 &
#             str_count(test_cat[length(test_cat)], "\\S+") == 1)) {
#           #Combine Service or Repair with the corresponding category being reviewed
#           paste(x, unlist(strsplit(test_cat[length(test_cat)], "[[:blank:]]")) %>%
#                   .[length(.)])
#           
#         }
#         #If the Repairing and Service are alone in any category and the current category is only a single word, combine the text with the singular category
#         else if (sum(grepl("\\bRepairing\\b|\\bService\\b", test_cat, fixed = F)) > 0 &
#                  str_count(x, "\\S+") == 1) {
#           c(x, paste(x, unlist(
#             strsplit(test_cat[grepl("\\bRepairing\\b|\\bService\\b|\\bRepair\\b",
#                                     test_cat,
#                                     fixed = F)], "[[:blank:]]")
#           ) %>%
#             .[length(.)]))
#           
#         }
#         #If cleaning exists in either of the categories, and the current word is a single item then append cleaning to the category in the selection
#         else if (sum(grepl("\\bCleaning\\b", test_cat, fixed = F)) > 0 &
#                  str_count(x, "\\S+") == 1) {
#           c(paste0(x, " Cleaning"), paste(x, unlist(
#             strsplit(test_cat[grepl("\\bCleaning\\b", test_cat, fixed = F)], "[[:blank:]]")
#           ) %>%
#             .[length(.)]))
#         }
#         else{
#           x
#         }
#       })), test_cat[length(test_cat)]) %>% gsub("- ", "", .) -> cats
#     } else {
#       test_cat -> cats
#     }
#     return(cats)
#   }))
unused_terms<-readRDS(here::here("data","unused_trends.RDS"))
# search_categories %<>% tidyr::unnest(search_categories) %>% as.data.frame()
# sc_tform <- search_categories %>% tidyr::unnest(search_categories) %>%
sc_tform <- tibble(search_categories = unique(c(categories_keywords, "bathroom repair","pest control"))) %>%
  dplyr::filter(
    !search_categories %in% unused_terms
  ) %>% 
  dplyr::mutate(
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Furniture", "Furniture Moving", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Tile", "Tile Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Trim", "Trim Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Windows", "Windows Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Storage", "Storage Service", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Paint", "Paint Services", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Carpet", "Carpet Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Bathroom", "Bathroom Repair", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Moving", "Moving Services", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Plumbing", "Plumbing Services", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Heating", "Heating Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Lighting", "Lighting Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Insulation", "Insulation Services", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Support", "Computer Support", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Blinds", "Blinds Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Mirrors", "Mirrors Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Roofing", "Roofing Installation", x)),
    search_categories = sapply(search_categories, function(x)
      `if`(x == "Lead", "Lead Removal", x)),
  ) %>%
  dplyr::filter(!search_categories %in% c("Installation")) %>%
  unique(.) %>%
  # dplyr::mutate(search_categories = purrr::map(search_categories,~{
  # case_when(
  #   .x=="Trim" ~ c(.x,paste0("Trim and Moldings Repair")),
  #   TRUE ~ .x
  # )
  # }))
  group_by(batch = row_number() %% round(nrow(.)/5,0)) %>%
  ungroup(.)
print(sc_tform, n = 100)

# first_cat <-
#   paste(test_cat[1], unlist(strsplit(test_cat[length(test_cat)], "[[:blank:]]")) %>%
#           .[length(.)])
# unlist(strsplit(test_cat[length(test_cat)], "[[:blank:]]"))
# str_count(test_cat, "\\S+")


date_start <- "2022-01-01"
date_end <- "2022-03-31"
start <- Sys.time()
time_span <- paste(date_start, date_end)
# ts_gtrends(
#   keyword = c("ukraine", "putin", "invasion"),
#   time = time_span,
#   geo     = "CA-ON"
# )->output_data_gt
geo_code <- "CA-ON"
lapply(0:max(sc_tform$batch), function(x) {
  sc_tform %>% dplyr::filter(batch == x) %>% pull(search_categories) %>% unique(.) -> keywords
  
  fname <-
    here::here("data",
               "batch-search-ww",
               paste0("batch-te-", x, "-", format(Sys.time(), "%Y%m%d"), ".RDS"))
  
  # print(keywords)
  if (!file.exists(fname)) {
    Sys.sleep(3)
    print(keywords)
    print(x)
    ts_gtrends(keyword = keywords,
               geo = geo_code,
               time = time_span) -> g_data
    saveRDS(g_data, file = fname)
  } else{
    readRDS(fname) -> g_data
  }
  g_data
}) -> all_gtrends_ontario
end <- Sys.time()
end - start

plot(all_gtrends_ontario[[1]])

search_trends <- all_gtrends_ontario %>% dplyr::bind_rows(.)

#Top searched results, likely a bad read on the category intention, need's an overlay
search_trends %>%
  group_by(id, mth = lubridate::month(time)) %>%
  summarise(value = sum(value, na.rm = T), .groups = "drop") %>%
  arrange(desc(value)) %>%
  group_by(id) %>%
  dplyr::mutate(tot_val = sum(value, na.rm = T)) %>%
  ungroup(.) %>%
  dplyr::mutate(rank = dense_rank(tot_val)) ->monthly_trends

monthly_trends%>%
  print(n=200)

if(exists("unused_terms")) {
  unused_terms <-
    unique(c(
      unused_terms,
      monthly_trends %>% dplyr::filter(value == 0) %>% dplyr::pull(id) %>% unique(.),
      "shopping","car rental","plumbing","food delivery","health services","fireplaces","architects","pet food","online course","online training", "asbestos","home add", "job search","stucco","real estate","online shopping","banking","online banking","travel","insurance","fireplace","demolition","decks","solar panel","vacuum","financial services"
    ))
} else{
  unused_terms <-
    monthly_trends %>% dplyr::filter(value == 0) %>% dplyr::pull(id) %>% unique(.)
}

if(!file.exists(here::here("data", "unused_trends.RDS"))) {
  saveRDS(unused_terms, file = here::here("data", "unused_trends.RDS"))
} else{
  saveRDS(unique(c(append(readRDS(
    here::here("data", "unused_trends.RDS")
  ), unused_terms))), here::here("data", "unused_trends.RDS"))
}
#Least searched results, likely a bad read on the category intention, need's an overlay
search_trends %>%
  group_by(id, mth = lubridate::month(time)) %>%
  summarise(value = sum(value, na.rm = T), .groups = "drop") %>%
  arrange(value) %>%
  group_by(id) %>%
  dplyr::mutate(tot_val = sum(value, na.rm = T)) %>%
  ungroup(.) %>%
  dplyr::mutate(rank = dense_rank(tot_val))

