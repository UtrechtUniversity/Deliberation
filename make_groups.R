#make groups 2026-11-04
#Rob Franken

rm(list=ls())
gc()

library(tidyverse)
library(ggplot2)

# function to sort subjects into groups, based on their discrimination attribution score [-10; 10]
# arguments are lists of male/female scores
# and the treatment for a 2x2 factorial design (heterogeneity x alignment

fcreategroups <- function(op_men, op_women,
                          heterogeneity = c("moderate", "strong"), #how much are men's/women's tiers mixed (pairing from adjacent or non-adjacent tiers)
                          alignment = c("aligned", "crossed")) { #whether women's tiers align with men's tiers or are reversed
  
  heterogeneity <- match.arg(heterogeneity)
  alignment <- match.arg(alignment)
  
  #heterogeneity = "moderate"
  #alignment = "crossed"
  
  if (length(op_men) != length(op_women)) stop("Number of men and women must be equal")
  
  N <- length(op_men)
  if (N %% 4 != 0) stop("N must be divisible by 4")
  
  n_per_tier <- N / 4
  
  # rank individuals within gender
  men_order <- order(op_men)
  women_order <- order(op_women)
  
  # split into 4 tiers
  split_tiers <- function(order_vec) split(order_vec, rep(1:4, each = n_per_tier))
  men_tiers <- split_tiers(men_order)
  women_tiers <- split_tiers(women_order)
  
  # define tier pairings for men
  # if heterogeneity is moderate, we pair men/women from adjacent tiers [e.g., the highest-ranked man-woman pair from tier 1 (3) is paired with the highest-ranked man-woman pair from tier 2 (4)] 
  # if heterogeneity is strong, we pair men/women from non-adjacent tiers [e.g., the highest-ranked man-woman pair from tier 1 (2) are paired with the highest-ranked man-woman pair from tier 3 (4)] 
  men_pairs <- if(heterogeneity == "moderate") list(c(1,2), c(3,4)) else list(c(1,3), c(2,4))
  
  # tier mapping for women
  women_map <- if(alignment == "aligned") 1:4 else c(4,3,2,1)
  
  groups <- list()
  g <- 1
  
  # loop through tier-pairs and within-tier ranks
  for(pair in men_pairs){ 
    # select subjects:
    # i-th ranked man in tier t1
    # i-th ranked man in tier t2
    # i-th ranked woman in mapped tier wt1
    # i-th ranked woman in mapped tier wt2
    
    t1 <- pair[1]; t2 <- pair[2]
    wt1 <- women_map[t1]; wt2 <- women_map[t2]
    
    for(i in 1:n_per_tier){
      ids <- c(
        men_tiers[[t1]][i], men_tiers[[t2]][i],
        women_tiers[[wt1]][i], women_tiers[[wt2]][i]
      )
      
      # assign rank within gender based on original ordering
      rank_within_gender <- c(
        match(men_tiers[[t1]][i], men_order),
        match(men_tiers[[t2]][i], men_order),
        match(women_tiers[[wt1]][i], women_order),
        match(women_tiers[[wt2]][i], women_order)
      )
      
      tier <- ceiling(rank_within_gender / n_per_tier)
      
      groups[[g]] <- data.frame(
        group_id = g,
        id = ids,
        gender = c("Male","Male","Female","Female"),
        opinion = c(op_men[ids[1:2]], op_women[ids[3:4]]),
        rank_within_gender = rank_within_gender,
        tier = tier
      )
      g <- g + 1
    }
  }
  
  do.call(rbind, groups)
}

#### test

set.seed(123) 

# 1. simulate scores for 20 men and 20 women [-10,10]
N <- 40
op_men <- sample(-10:10, N, replace = TRUE)
op_women <- sample(-10:10, N, replace = TRUE)

# 2. define treatments
treatments <- expand.grid(
  heterogeneity = c("moderate", "strong"),
  alignment = c("aligned", "crossed"),
  stringsAsFactors = FALSE
)

# 3. generate groups for each treatment

fcreategroups(op_men, op_women, "moderate", "crossed")

all_groups <- lapply(1:nrow(treatments), function(i) {
  fcreategroups(
    op_men = op_men,
    op_women = op_women,
    heterogeneity = treatments$heterogeneity[i],
    alignment = treatments$alignment[i]
  ) %>%
    mutate(
      heterogeneity = treatments$heterogeneity[i],
      alignment = treatments$alignment[i]
    )
}) %>% bind_rows()


# adjust factor labels
all_groups <- all_groups %>%
  mutate(
    heterogeneity = factor(heterogeneity, levels = c("moderate", "strong"),
                           labels = c("Moderate heterogeniety", "Strong heterogeneity")),
    alignment = factor(alignment, levels = c("aligned", "crossed"),
                       labels = c("Male/female tiers align", "Male/female tiers cross"))
  )

#plot:
tier_shades <- data.frame(
  ymin = c(1, 6, 11, 16) - 0.5, 
  ymax = c(5, 10, 15, 20) + 0.5, 
  tier = factor(1:4)
)
tier_colors <- c("#f0f0f0", "#d9d9d9", "#bdbdbd", "#969696")


p <- ggplot(all_groups, aes(x = factor(group_id), y = rank_within_gender, color = gender)) +
  geom_rect(
    data = tier_shades,
    aes(xmin = -Inf, xmax = Inf, ymin = ymin, ymax = ymax, fill = tier),
    inherit.aes = FALSE,
    alpha = 0.4
  ) +
  geom_line(aes(group = interaction(group_id, gender)), color = "grey70",
            position = position_dodge(width = 0.4)) +
  geom_point(size = 1.5, position = position_dodge(width = 0.4)) +
  facet_grid(heterogeneity ~ alignment) +
  labs(
    x = "Group ID",
    y = "Rank (within-gender)",
    color = "Gender",
    fill = "Tier",
    title = "Grouping of subjects based on 2x2 design"
  ) +
  theme_bw() +
  scale_fill_manual(values = tier_colors)

p

ggsave("grouping_plot.png", plot = p, width = 8, height = 6, dpi = 300)
