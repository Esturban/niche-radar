require(rvest)
"https://reverbico.com/blog/top-big-data-consulting-companies/"%>%
  read_html()%>%
  html_nodes('strong a')%>%
  html_attr("href")%>%
  gsub("/","",.)%>%
  paste0("https://",.)->competitor_links
competitor_links<-unique(c("https://www.analytics8.com/","https://consultport.com/","https://www.acxiom.com/",competitor_links))

saveRDS(object = competitor_links,file ="../website-functions/data/eva-competitors.RDS")
