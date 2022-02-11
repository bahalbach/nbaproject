function search(nums: number[], target: number): number {
  if (nums.length === 0) {
    return -1;
  }
  function helper(start: number, end: number): number {
    if (start < end - 1) {
      let mid = Math.floor((start + end) / 2);
      if (nums[mid] === target) {
        return mid;
      } else if (nums[mid] > target) {
        return helper(start, mid);
      } else {
        return helper(start + 1, end);
      }
    }

    if (start === end) return -1;
    if (nums[start] === target) {
      return start;
    }
    return -1;
  }
  return helper(0, nums.length);
}

console.log(search([0], 0) === 0);
console.log(search([1], 0) === -1);
console.log(search([0, 1], 0) === 0);
console.log(search([0, 1], -1) === -1);
console.log(search([0, 1], 1) === 1);
console.log(search([0, 1], 2) === -1);
console.log(search([0, 1, 2], 1) === 1);
console.log(search([0, 1, 2], 0) === 0);
console.log(search([0, 1, 2], 2) === 2);
console.log(search([0, 1, 2], -1) === -1);
console.log(search([0, 1, 2], 3) === -1);
